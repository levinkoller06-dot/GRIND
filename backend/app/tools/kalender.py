from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.tools.base import ToolContext, obj, propose, tool

KINDS = ["schule", "termin", "test", "geburtstag", "sonstiges"]


def event_times(payload: dict, tz: ZoneInfo) -> tuple[datetime, datetime | None, bool]:
    """Wandelt Datum/Uhrzeit aus einem Vorschlag in Zeitstempel um."""
    day = date.fromisoformat(payload["datum"])
    start_time = payload.get("uhrzeit")
    if not start_time:
        return datetime.combine(day, time.min, tz), None, True
    start = datetime.combine(day, time.fromisoformat(start_time), tz)
    end_time = payload.get("ende_uhrzeit")
    end = datetime.combine(day, time.fromisoformat(end_time), tz) if end_time else None
    if end and end <= start:
        end += timedelta(days=1)
    return start, end, False


def describe(payload: dict) -> str:
    when = payload["datum"] + (f" {payload['uhrzeit']}" if payload.get("uhrzeit") else "")
    extra = (f" in/bei {payload['ort']}" if payload.get("ort") else "") + (
        f" mit {', '.join(payload['mit'])}" if payload.get("mit") else ""
    )
    return f"Termin „{payload['titel']}“ am {when}{extra}."


@tool(
    "termin_vorschlagen",
    "Schlägt einen Kalendertermin vor. Der Termin wird erst eingetragen, wenn der Nutzer "
    "bestätigt. Für Tests/Klassenarbeiten stattdessen test_anlegen verwenden.",
    obj(
        {
            "titel": {"type": "string", "description": "Kurzer Titel, z. B. 'Zahnarzt'"},
            "datum": {"type": "string", "description": "Datum im Format YYYY-MM-DD"},
            "uhrzeit": {"type": "string", "description": "Startzeit HH:MM, weglassen = ganztägig"},
            "ende_uhrzeit": {"type": "string", "description": "Endzeit HH:MM (optional)"},
            "art": {"type": "string", "enum": KINDS},
            "ort": {
                "type": "string",
                "description": "Wo, z. B. 'Kino Pathé' oder 'Zahnarzt Dr. Meier'",
            },
            "mit": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Mit wem, z. B. ['Tim', 'Lea']",
            },
            "notiz": {"type": "string"},
        },
        ["titel", "datum"],
    ),
)
async def termin_vorschlagen(ctx: ToolContext, args: dict) -> dict:
    payload = {k: v for k, v in args.items() if v not in (None, "", [])}
    payload.setdefault("art", "termin")
    event_times(payload, ctx.tz)  # prüft das Format, bevor der Vorschlag entsteht
    return await propose(ctx, "event.create", payload, describe(payload))


@tool(
    "termine_abfragen",
    "Listet Termine (inkl. Tests) in einem Zeitraum auf.",
    obj(
        {
            "von": {"type": "string", "description": "YYYY-MM-DD, Standard: heute"},
            "bis": {"type": "string", "description": "YYYY-MM-DD, Standard: in 14 Tagen"},
        }
    ),
)
async def termine_abfragen(ctx: ToolContext, args: dict) -> dict:
    today = ctx.now.date()
    start = date.fromisoformat(args.get("von") or today.isoformat())
    end = date.fromisoformat(args.get("bis") or (today + timedelta(days=14)).isoformat())
    rows = await ctx.db.select(
        "events",
        select="id,title,starts_at,ends_at,all_day,kind,location,participants",
        order="starts_at",
        **{
            "starts_at": f"gte.{datetime.combine(start, time.min, ctx.tz).isoformat()}",
            "and": f"(starts_at.lt.{datetime.combine(end + timedelta(days=1), time.min, ctx.tz).isoformat()})",
        },
    )
    return {"termine": rows}


@tool(
    "termin_loeschen",
    "Schlägt vor, einen Termin zu löschen (der Nutzer muss bestätigen). Die ID vorher mit "
    "termine_abfragen herausfinden. Gehört der Termin zu einem Test, wird der Test mitgelöscht.",
    obj({"id": {"type": "string", "description": "ID aus termine_abfragen"}}, ["id"]),
)
async def termin_loeschen(ctx: ToolContext, args: dict) -> dict:
    rows = await ctx.db.select("events", id=f"eq.{args['id']}")
    if not rows:
        raise ValueError("Termin nicht gefunden – erst termine_abfragen aufrufen")
    event = rows[0]
    start = datetime.fromisoformat(event["starts_at"]).astimezone(ctx.tz)
    payload = {
        "event_id": event["id"],
        "titel": event["title"],
        "datum": start.date().isoformat(),
        "art": event.get("kind") or "termin",
    }
    if not event.get("all_day"):
        payload["uhrzeit"] = start.strftime("%H:%M")
    if event.get("location"):
        payload["ort"] = event["location"]
    return await propose(ctx, "event.delete", payload, f"Löschen von {describe(payload)}")
