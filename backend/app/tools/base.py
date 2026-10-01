from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.config import get_settings
from app.db import Db


@dataclass
class ToolContext:
    db: Db
    tz: ZoneInfo
    now: datetime
    grade_scale: str = "ch"
    # Vorschläge, die während dieser Anfrage entstanden sind (für die App)
    pending: list[dict] = field(default_factory=list)


Handler = Callable[[ToolContext, dict[str, Any]], Awaitable[dict[str, Any]]]


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Handler

    def declaration(self) -> dict:
        return {"name": self.name, "description": self.description, "parameters": self.parameters}


REGISTRY: dict[str, Tool] = {}


def tool(name: str, description: str, parameters: dict[str, Any]):
    """Registriert eine Funktion als Tool für das Gehirn."""

    def register(fn: Handler) -> Handler:
        REGISTRY[name] = Tool(name, description, parameters, fn)
        return fn

    return register


def obj(properties: dict[str, Any], required: list[str] | None = None) -> dict:
    return {"type": "object", "properties": properties, "required": required or []}


async def propose(ctx: ToolContext, kind: str, payload: dict, summary: str) -> dict:
    """Legt einen Vorschlag an, den der Nutzer erst bestätigen muss.

    Ist CONFIRM_ACTIONS aus, wird der Vorschlag sofort ausgeführt (und als bestätigt gespeichert).
    """
    from app import actions  # erst hier, sonst zirkulärer Import

    row = await ctx.db.insert(
        "pending_actions",
        {"user_id": ctx.db.user.id, "kind": kind, "payload": payload, "source": "chat"},
    )
    if not get_settings().confirm_actions:
        try:
            done = await actions.decide(ctx.db, row["id"], True, {}, ctx.tz)
        except actions.ActionError as e:
            return {"status": "fehlgeschlagen", "fehler": str(e)}
        return {
            "status": "erledigt",
            "ergebnis": done.get("result"),
            "hinweis": f"{summary} Ist schon erledigt, der Nutzer muss nichts mehr bestätigen.",
        }
    ctx.pending.append(row)
    return {
        "status": "vorgeschlagen",
        "hinweis": f"{summary} Der Nutzer muss das in der App noch bestätigen. "
        "Sag ihm, dass der Vorschlag bereitliegt, und behaupte nicht, es sei schon eingetragen.",
    }
