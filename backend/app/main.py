import asyncio
import logging
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app import actions, harness, suggestions
from app.auth import UserDep
from app.config import Settings, get_settings
from app.db import Db, DbError
from app.llm import Gemini, LlmError
from app.mail import service as mail_service
from app.mail.imap import PRESETS, MailError

log = logging.getLogger(__name__)

app = FastAPI(title="GRIND Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().frontend_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(DbError)
async def db_error(_: Request, exc: DbError) -> JSONResponse:
    # Fehlt eine Tabelle/Spalte, wurde meist eine Migration noch nicht ausgeführt
    missing = "PGRST204" in str(exc) or "PGRST205" in str(exc) or "42703" in str(exc)
    detail = (
        "Datenbank ist nicht aktuell: bitte die neuen SQL-Dateien aus supabase/migrations ausführen."
        if missing
        else f"Datenbank-Fehler: {exc}"
    )
    return JSONResponse({"detail": detail}, status_code=500)


@app.exception_handler(MailError)
async def mail_error(_: Request, exc: MailError) -> JSONResponse:
    return JSONResponse({"detail": str(exc)}, status_code=400)


SettingsDep = Annotated[Settings, Depends(get_settings)]


async def get_db(user: UserDep, settings: SettingsDep):
    async with Db(user, settings) as db:
        yield db


DbDep = Annotated[Db, Depends(get_db)]


def get_llm(settings: SettingsDep) -> Gemini:
    if not settings.gemini_api_key:
        raise HTTPException(503, "GEMINI_API_KEY fehlt in backend/.env")
    return Gemini(settings.gemini_api_key, [m.strip() for m in settings.gemini_models.split(",")])


async def user_tz(db: Db) -> ZoneInfo:
    rows = await db.select("profiles", select="timezone", id=f"eq.{db.user.id}")
    return ZoneInfo(rows[0]["timezone"] if rows else "Europe/Berlin")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/me")
async def me(db: DbDep) -> dict:
    rows = await db.select("profiles", id=f"eq.{db.user.id}")
    return {"user_id": db.user.id, "email": db.user.email, "profile": rows[0] if rows else None}


class ImageIn(BaseModel):
    mime_type: str = Field(pattern=r"^image/(jpeg|png|webp)$")
    data: str = Field(max_length=4_000_000)  # base64, ca. 3 MB


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    image: ImageIn | None = None


_chat_locks: dict[str, asyncio.Lock] = {}


@app.post("/chat")
async def chat(body: ChatIn, db: DbDep, llm: Annotated[Gemini, Depends(get_llm)]) -> dict:
    lock = _chat_locks.setdefault(db.user.id, asyncio.Lock())
    async with lock:
        try:
            image = body.image.model_dump() if body.image else None
            return await harness.chat(db, llm, body.message.strip(), image)
        except harness.LimitReached as e:
            raise HTTPException(429, str(e)) from e
        except LlmError as e:
            raise HTTPException(502, str(e)) from e
        except (DbError, MailError):
            raise
        except Exception as e:  # sauber melden statt "Backend nicht erreichbar"
            log.exception("Chat fehlgeschlagen")
            raise HTTPException(500, f"Interner Fehler: {e}") from e


@app.get("/chat/history")
async def chat_history(db: DbDep) -> list[dict]:
    rows = await db.select(
        "chat_messages",
        select="id,role,content,created_at",
        role="in.(user,assistant)",
        order="created_at.desc",
        limit="50",
    )
    return list(reversed(rows))


@app.get("/nutrition/suggestions")
async def nutrition_suggestions(db: DbDep, llm: Annotated[Gemini, Depends(get_llm)]) -> dict:
    try:
        return await suggestions.suggestions(db, llm, await user_tz(db))
    except LlmError as e:
        raise HTTPException(502, str(e)) from e


class MailAccountIn(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=1, max_length=500)
    preset: str | None = None
    label: str | None = Field(default=None, max_length=40)
    color: str | None = None
    imap_host: str | None = None
    imap_port: int | None = None
    smtp_host: str | None = None
    smtp_port: int | None = None


@app.get("/mail/presets")
def mail_presets() -> dict:
    return PRESETS


@app.get("/mail/accounts")
async def mail_accounts(db: DbDep) -> list[dict]:
    return await mail_service.list_accounts(db)


@app.post("/mail/accounts")
async def add_mail_account(body: MailAccountIn, db: DbDep) -> dict:
    return await mail_service.add_account(db, body.model_dump())


@app.delete("/mail/accounts/{account_id}")
async def delete_mail_account(account_id: str, db: DbDep) -> dict:
    await db.delete("mail_accounts", id=f"eq.{account_id}")
    return {"geloescht": True}


@app.get("/mail/inbox")
async def mail_inbox(db: DbDep, days: int = 7) -> dict:
    return await mail_service.inbox(db, days=min(days, 30), limit=40)


@app.get("/mail/message/{mail_id}")
async def mail_message(mail_id: str, db: DbDep) -> dict:
    return await mail_service.read(db, mail_id)


@app.get("/pending")
async def pending(db: DbDep) -> list[dict]:
    return await db.select("pending_actions", status="eq.open", order="created_at")


class DecisionIn(BaseModel):
    changes: dict = {}


@app.post("/pending/{action_id}/confirm")
async def confirm(action_id: str, body: DecisionIn, db: DbDep) -> dict:
    try:
        return await actions.decide(db, action_id, True, body.changes, await user_tz(db))
    except actions.ActionError as e:
        raise HTTPException(400, str(e)) from e


@app.post("/pending/{action_id}/reject")
async def reject(action_id: str, db: DbDep) -> dict:
    try:
        return await actions.decide(db, action_id, False, {}, await user_tz(db))
    except actions.ActionError as e:
        raise HTTPException(400, str(e)) from e
