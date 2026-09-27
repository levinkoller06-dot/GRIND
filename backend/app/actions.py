"""Ausführen bestätigter Vorschläge (pending_actions)."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.db import Db
from app.tools.kalender import event_times


class ActionError(Exception):
    pass


async def _create_event(db: Db, payload: dict, tz: ZoneInfo) -> dict:
    start, end, all_day = event_times(payload, tz)
    row = {
        "user_id": db.user.id,
        "title": payload["titel"],
        "starts_at": start.isoformat(),
        "ends_at": end.isoformat() if end else None,
        "all_day": all_day,
        "kind": payload.get("art", "termin"),
        "notes": payload.get("notiz"),
        "exam_id": payload.get("exam_id"),
    }
    if payload.get("ort"):
        row["location"] = payload["ort"]
    if payload.get("mit"):
        row["participants"] = payload["mit"]
    return await db.insert("events", row)


async def _delete_event(db: Db, payload: dict, tz: ZoneInfo) -> dict:
    rows = await db.select("events", select="id,exam_id", id=f"eq.{payload['event_id']}")
    if not rows:
        raise ActionError("Termin gibt es nicht mehr")
    await db.delete("events", id=f"eq.{payload['event_id']}")
    if rows[0].get("exam_id"):
        await db.delete("exams", id=f"eq.{rows[0]['exam_id']}")
    return {"geloescht": True}


EXECUTORS = {"event.create": _create_event, "event.delete": _delete_event}

EDITABLE = {"titel", "datum", "uhrzeit", "ende_uhrzeit", "art", "notiz", "ort", "mit"}


async def decide(db: Db, action_id: str, confirm: bool, changes: dict, tz: ZoneInfo) -> dict:
    rows = await db.select("pending_actions", id=f"eq.{action_id}")
    if not rows:
        raise ActionError("Vorschlag nicht gefunden")
    action = rows[0]
    if action["status"] != "open":
        raise ActionError("Vorschlag wurde schon entschieden")

    now = datetime.now(UTC).isoformat()
    if not confirm:
        await db.update(
            "pending_actions", {"status": "rejected", "decided_at": now}, id=f"eq.{action_id}"
        )
        return {"status": "rejected"}

    payload = action["payload"] | {k: v for k, v in changes.items() if k in EDITABLE}
    payload = {k: v for k, v in payload.items() if v not in (None, "", [])}
    executor = EXECUTORS.get(action["kind"])
    if executor is None:
        raise ActionError(f"Unbekannte Aktion: {action['kind']}")

    try:
        result = await executor(db, payload, tz)
    except ValueError as e:
        raise ActionError(f"Ungültige Angaben: {e}") from e

    await db.update(
        "pending_actions",
        {"status": "confirmed", "decided_at": now, "payload": payload},
        id=f"eq.{action_id}",
    )
    return {"status": "confirmed", "result": result}
