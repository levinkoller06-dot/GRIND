from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import UserDep
from app.config import Settings, get_settings
from app.db import user_client

app = FastAPI(title="GRIND Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().frontend_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/me")
async def me(user: UserDep, settings: Annotated[Settings, Depends(get_settings)]) -> dict:
    async with user_client(user, settings) as db:
        res = await db.get("/profiles", params={"id": f"eq.{user.id}", "select": "*"})
    profile = res.json()[0] if res.is_success and res.json() else None
    return {"user_id": user.id, "email": user.email, "profile": profile}
