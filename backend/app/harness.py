"""Das Gehirn: Nachricht → Gemini → Tool-Aufrufe → Antwort."""

import json
import logging
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.db import Db
from app.llm import Gemini
from app.tools import REGISTRY, ToolContext

log = logging.getLogger(__name__)

MAX_STEPS = 6
HISTORY = 20
WEEKDAYS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]


class LimitReached(Exception):
    pass


def system_prompt(now: datetime, name: str | None) -> str:
    days = "\n".join(
        f"- {WEEKDAYS[d.weekday()]}: {d.isoformat()}"
        for d in (now.date() + timedelta(days=i) for i in range(8))
    )
    return f"""Du bist das Gehirn von GRIND, einer Alltags-App für Schule, Gym und Leben.
Du sprichst Deutsch, locker und kurz (wie ein guter Kumpel), du duzt den Nutzer{f" ({name})" if name else ""}.

Jetzt ist {WEEKDAYS[now.weekday()]}, {now.strftime("%d.%m.%Y %H:%M")} (Zeitzone {now.tzinfo}).
Die nächsten Tage:
{days}
„Donnerstag“ meint immer den nächsten Donnerstag ab heute (heute zählt, wenn heute Donnerstag ist und der Kontext passt).

Regeln:
- Eine Nachricht kann mehrere Dinge enthalten. Erledige alle mit den passenden Tools, gern mehrere Tools auf einmal.
- Termine werden nie direkt eingetragen, sondern nur vorgeschlagen. Der Nutzer bestätigt sie in der App.
  Sag also z. B. „Hab dir den Termin zum Bestätigen hingelegt“, nie „eingetragen“.
- Tests/Klassenarbeiten immer mit test_anlegen, nicht mit termin_vorschlagen.
- Erfinde keine Daten. Wenn etwas Wichtiges fehlt (z. B. welches Fach), frag kurz nach.
- Wenn es kein passendes Tool gibt, sag ehrlich, dass du das noch nicht kannst.
- Antworte kurz: 1–3 Sätze, Emojis sparsam."""


async def check_limit(db: Db, now: datetime, limit: int) -> None:
    midnight = datetime.combine(now.date(), time.min, now.tzinfo).isoformat()
    today = await db.select(
        "chat_messages", select="id", role="eq.user", created_at=f"gte.{midnight}"
    )
    if len(today) >= limit:
        raise LimitReached(f"Tageslimit von {limit} Nachrichten erreicht. Morgen geht's weiter!")


async def load_history(db: Db) -> list[dict]:
    rows = await db.select(
        "chat_messages",
        select="role,content",
        role="in.(user,assistant)",
        order="created_at.desc",
        limit=str(HISTORY),
    )
    return [
        {"role": "model" if r["role"] == "assistant" else "user", "parts": [{"text": r["content"]}]}
        for r in reversed(rows)
    ]


async def run_tool(ctx: ToolContext, call: dict) -> dict:
    name, args = call["name"], call.get("args") or {}
    tool = REGISTRY.get(name)
    ok = True
    try:
        if tool is None:
            raise ValueError(f"Unbekanntes Tool: {name}")
        result = await tool.handler(ctx, args)
    except Exception as e:  # Fehler an die KI zurückgeben, damit sie reagieren kann
        log.exception("Tool %s fehlgeschlagen", name)
        ok = False
        result = {"fehler": str(e)}
    await ctx.db.insert(
        "tool_log",
        {
            "user_id": ctx.db.user.id,
            "tool": name,
            "arguments": args,
            "result": json.loads(json.dumps(result, default=str)),
            "ok": ok,
        },
    )
    return result


async def chat(db: Db, llm: Gemini, message: str) -> dict:
    profiles = await db.select("profiles", id=f"eq.{db.user.id}")
    profile = profiles[0] if profiles else {}
    tz = ZoneInfo(profile.get("timezone") or "Europe/Berlin")
    now = datetime.now(tz)

    await check_limit(db, now, profile.get("ai_daily_limit") or 100)

    contents = await load_history(db)
    contents.append({"role": "user", "parts": [{"text": message}]})
    await db.insert("chat_messages", {"user_id": db.user.id, "role": "user", "content": message})

    ctx = ToolContext(db=db, tz=tz, now=now)
    declarations = [t.declaration() for t in REGISTRY.values()]
    system = system_prompt(now, profile.get("display_name"))
    tools_used: list[str] = []
    reply = ""

    for _ in range(MAX_STEPS):
        content = await llm.generate(system, contents, declarations)
        # Unverändert zurückgeben (enthält bei Gemini 3 die "thought signatures")
        contents.append(content)
        parts = content.get("parts", [])
        calls = [p["functionCall"] for p in parts if "functionCall" in p]
        if not calls:
            reply = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
            break
        responses = []
        for call in calls:
            tools_used.append(call["name"])
            response = {"name": call["name"], "response": await run_tool(ctx, call)}
            if call.get("id"):
                response["id"] = call["id"]
            responses.append({"functionResponse": response})
        contents.append({"role": "user", "parts": responses})
    else:
        reply = "Puh, das war zu viel auf einmal. Kannst du es aufteilen?"

    reply = reply or "Erledigt."
    await db.insert("chat_messages", {"user_id": db.user.id, "role": "assistant", "content": reply})
    return {"reply": reply, "pending": ctx.pending, "tools": tools_used}
