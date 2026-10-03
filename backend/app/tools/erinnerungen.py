from datetime import date, datetime, time, timedelta

from app.tools.base import ToolContext, obj, tool


@tool(
    "erinnerung_setzen",
    "Setzt eine Erinnerung, die zur gewünschten Zeit als Meldung in der App erscheint "
    "(z. B. 'erinner mich morgen um 7 an die Sporttasche' oder 'in 20 Minuten an den Ofen').",
    obj(
        {
            "text": {
                "type": "string",
                "description": "Woran erinnert werden soll, z. B. 'Sporttasche packen'",
            },
            "datum": {"type": "string", "description": "YYYY-MM-DD, Standard: heute"},
            "uhrzeit": {"type": "string", "description": "HH:MM, Standard: 07:00"},
            "in_minuten": {
                "type": "integer",
                "description": "Statt Datum/Uhrzeit: in so vielen Minuten ab jetzt",
            },
        },
        ["text"],
    ),
)
async def erinnerung_setzen(ctx: ToolContext, args: dict) -> dict:
    if args.get("in_minuten"):
        due = ctx.now + timedelta(minutes=int(args["in_minuten"]))
    else:
        day = date.fromisoformat(args.get("datum") or ctx.now.date().isoformat())
        due = datetime.combine(day, time.fromisoformat(args.get("uhrzeit") or "07:00"), ctx.tz)
    if due <= ctx.now:
        return {"fehler": "Dieser Zeitpunkt ist schon vorbei. Frag nach einer späteren Zeit."}
    row = await ctx.db.insert(
        "reminders",
        {"user_id": ctx.db.user.id, "text": args["text"].strip(), "due_at": due.isoformat()},
    )
    return {"gespeichert": True, "id": row["id"], "wann": due.strftime("%Y-%m-%d %H:%M")}


@tool(
    "erinnerungen_abfragen",
    "Listet die offenen (noch nicht fälligen) Erinnerungen auf.",
    obj({}),
)
async def erinnerungen_abfragen(ctx: ToolContext, args: dict) -> dict:
    rows = await ctx.db.select(
        "reminders", select="id,text,due_at,done_at", done_at="is.null", order="due_at"
    )
    return {
        "erinnerungen": [
            {
                "id": r["id"],
                "text": r["text"],
                "wann": datetime.fromisoformat(r["due_at"])
                .astimezone(ctx.tz)
                .strftime("%Y-%m-%d %H:%M"),
            }
            for r in rows
            if not r.get("done_at")
        ]
    }


@tool(
    "erinnerung_loeschen",
    "Löscht eine Erinnerung. Die ID vorher mit erinnerungen_abfragen holen.",
    obj({"id": {"type": "string"}}, ["id"]),
)
async def erinnerung_loeschen(ctx: ToolContext, args: dict) -> dict:
    await ctx.db.delete("reminders", id=f"eq.{args['id']}")
    return {"geloescht": True}
