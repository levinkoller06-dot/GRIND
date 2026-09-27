from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app import actions, harness
from app.auth import UserDep
from app.config import Settings, get_settings
from app.db import Db
from app.llm import Gemini, LlmError

app = FastAPI(title="GRIND Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().frontend_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

SettingsDep = Annotated[Settings, Depends(get_settings)]


async def get_db(user: UserDep, settings: SettingsDep):
    async with Db(user, settings) as db:
        yield db


DbDep = Annotated[Db, Depends(get_db)]


def get_llm(settings: SettingsDep) -> Gemini:
    if not settings.gemini_api_key:
        raise HTTPException(503, "GEMINI_API_KEY fehlt in backend/.env")
    return Gemini(settings.gemini_api_key, settings.gemini_model, settings.gemini_fallback_model)


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


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


@app.post("/chat")
async def chat(body: ChatIn, db: DbDep, llm: Annotated[Gemini, Depends(get_llm)]) -> dict:
    try:
        return await harness.chat(db, llm, body.message.strip())
    except harness.LimitReached as e:
        raise HTTPException(429, str(e)) from e
    except LlmError as e:
        raise HTTPException(502, f"KI nicht erreichbar: {e}") from e


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
