from datetime import date, timedelta

from app.tools.base import ToolContext, obj, tool

ENTRY = obj(
    {
        "uebung": {"type": "string", "description": "z. B. 'Liegestütze', 'Bankdrücken', 'Laufen'"},
        "saetze": {"type": "integer"},
        "wiederholungen": {"type": "integer", "description": "pro Satz"},
        "gewicht_kg": {"type": "number"},
        "dauer_min": {"type": "number"},
        "distanz_km": {"type": "number"},
    },
    ["uebung"],
)

FIELDS = {
    "uebung": "exercise",
    "saetze": "sets",
    "wiederholungen": "reps",
    "gewicht_kg": "weight_kg",
    "dauer_min": "duration_min",
    "distanz_km": "distance_km",
}


def _num(v) -> float:
    return float(v) if v not in (None, "") else 0.0


def records(entries: list[dict]) -> dict[str, dict]:
    """Bestwerte pro Übung (Schlüssel: Übung in Kleinbuchstaben)."""
    best: dict[str, dict] = {}
    for e in entries:
        key = e["exercise"].strip().lower()
        b = best.setdefault(
            key,
            {
                "uebung": e["exercise"],
                "max_gewicht_kg": 0.0,
                "max_wiederholungen": 0.0,
                "max_distanz_km": 0.0,
            },
        )
        b["max_gewicht_kg"] = max(b["max_gewicht_kg"], _num(e.get("weight_kg")))
        b["max_wiederholungen"] = max(b["max_wiederholungen"], _num(e.get("reps")))
        b["max_distanz_km"] = max(b["max_distanz_km"], _num(e.get("distance_km")))
    return best


def new_records(entry: dict, previous: dict | None) -> list[str]:
    if previous is None:
        return []
    found = []
    if _num(entry.get("weight_kg")) > previous["max_gewicht_kg"] > 0:
        found.append(f"Neuer Gewichts-Rekord: {entry['weight_kg']} kg")
    elif (
        not entry.get("weight_kg") and _num(entry.get("reps")) > previous["max_wiederholungen"] > 0
    ):
        found.append(f"Neuer Wiederholungs-Rekord: {entry['reps']}")
    if _num(entry.get("distance_km")) > previous["max_distanz_km"] > 0:
        found.append(f"Neuer Distanz-Rekord: {entry['distance_km']} km")
    return found


@tool(
    "training_speichern",
    "Speichert ein Training mit einer oder mehreren Übungen und meldet neue Rekorde.",
    obj(
        {
            "uebungen": {"type": "array", "items": ENTRY},
            "titel": {
                "type": "string",
                "description": "z. B. 'Push', 'Beine', 'Laufen' (optional)",
            },
            "datum": {"type": "string", "description": "YYYY-MM-DD, Standard: heute"},
            "notiz": {"type": "string"},
        },
        ["uebungen"],
    ),
)
async def training_speichern(ctx: ToolContext, args: dict) -> dict:
    day = args.get("datum") or ctx.now.date().isoformat()
    date.fromisoformat(day)
    uid = ctx.db.user.id
    before = records(await ctx.db.select("workout_entries"))

    workout = await ctx.db.insert(
        "workouts",
        {"user_id": uid, "date": day, "title": args.get("titel"), "notes": args.get("notiz")},
    )
    rows = [
        {"user_id": uid, "workout_id": workout["id"]}
        | {FIELDS[k]: v for k, v in e.items() if k in FIELDS and v not in (None, "", 0)}
        for e in args["uebungen"]
    ]
    saved = await ctx.db.insert_many("workout_entries", rows)
    prs = [
        f"{e['exercise']}: {pr}"
        for e in saved
        for pr in new_records(e, before.get(e["exercise"].strip().lower()))
    ]
    return {
        "gespeichert": True,
        "training_id": workout["id"],
        "uebungen": len(saved),
        "neue_rekorde": prs,
    }


@tool(
    "trainings_abfragen",
    "Listet Trainings in einem Zeitraum (Standard: letzte 14 Tage), optional nur eine Übung.",
    obj(
        {
            "von": {"type": "string", "description": "YYYY-MM-DD"},
            "bis": {"type": "string", "description": "YYYY-MM-DD"},
            "uebung": {"type": "string"},
        }
    ),
)
async def trainings_abfragen(ctx: ToolContext, args: dict) -> dict:
    today = ctx.now.date()
    start = args.get("von") or (today - timedelta(days=14)).isoformat()
    end = args.get("bis") or today.isoformat()
    workouts = await ctx.db.select(
        "workouts",
        select="id,date,title,notes,workout_entries(exercise,sets,reps,weight_kg,duration_min,distance_km)",
        date=f"gte.{start}",
        order="date.desc",
        **{"and": f"(date.lte.{end})"},
    )
    if args.get("uebung"):
        needle = args["uebung"].strip().lower()
        for w in workouts:
            w["workout_entries"] = [
                e for e in w["workout_entries"] if needle in e["exercise"].lower()
            ]
        workouts = [w for w in workouts if w["workout_entries"]]
    return {"trainings": workouts}


@tool(
    "rekorde_abfragen",
    "Gibt die Bestwerte (Gewicht, Wiederholungen, Distanz) pro Übung zurück.",
    obj({"uebung": {"type": "string", "description": "Optional, sonst alle"}}),
)
async def rekorde_abfragen(ctx: ToolContext, args: dict) -> dict:
    best = records(await ctx.db.select("workout_entries"))
    if args.get("uebung"):
        needle = args["uebung"].strip().lower()
        best = {k: v for k, v in best.items() if needle in k}
    return {"rekorde": list(best.values())}


WEEKDAYS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]

PLAN_EXERCISE = obj(
    {
        "uebung": {"type": "string"},
        "saetze": {"type": "integer"},
        "wiederholungen": {"type": "integer"},
        "dauer": {"type": "string", "description": "z. B. '1 Minute', '20–30 Minuten'"},
        "stufe": {
            "type": "string",
            "description": "Gewicht/Geräte-Stufe, z. B. bei 'Brustpresse – 3×8 -11' → '11'",
        },
        "hinweis": {"type": "string"},
    },
    ["uebung"],
)

PLAN_DAY = obj(
    {
        "tag": {
            "type": "string",
            "description": "Wochentag(e), z. B. 'Montag' oder 'Samstag oder Sonntag'",
        },
        "titel": {"type": "string", "description": "z. B. 'Brust & Rücken' oder 'Pause'"},
        "pause": {"type": "boolean"},
        "uebungen": {"type": "array", "items": PLAN_EXERCISE},
        "hinweis": {"type": "string", "description": "z. B. 'Kompletter Ruhetag'"},
    },
    ["tag", "titel"],
)


async def _load_plan(ctx: ToolContext) -> list[dict]:
    rows = await ctx.db.select("training_plans", user_id=f"eq.{ctx.db.user.id}")
    return rows[0]["days"] if rows else []


async def _save_plan(ctx: ToolContext, days: list[dict]) -> None:
    uid = ctx.db.user.id
    if await ctx.db.select("training_plans", select="user_id", user_id=f"eq.{uid}"):
        await ctx.db.update(
            "training_plans",
            {"days": days, "updated_at": ctx.now.isoformat()},
            user_id=f"eq.{uid}",
        )
    else:
        await ctx.db.insert("training_plans", {"user_id": uid, "days": days})


def _clean(day: dict) -> dict:
    day = {k: v for k, v in day.items() if v not in (None, "", [])}
    day["uebungen"] = [
        {k: v for k, v in e.items() if v not in (None, "", 0)} for e in day.get("uebungen", [])
    ]
    day["pause"] = bool(day.get("pause"))
    return day


@tool(
    "trainingsplan_setzen",
    "Speichert den kompletten Wochen-Trainingsplan (ersetzt den alten). Übernimm alle Tage "
    "in der Reihenfolge des Nutzers, auch Pausentage.",
    obj({"tage": {"type": "array", "items": PLAN_DAY}}, ["tage"]),
)
async def trainingsplan_setzen(ctx: ToolContext, args: dict) -> dict:
    days = [_clean(d) for d in args["tage"]]
    await _save_plan(ctx, days)
    return {
        "gespeichert": True,
        "tage": len(days),
        "uebungen": sum(len(d["uebungen"]) for d in days),
    }


@tool(
    "trainingsplan_tag_aendern",
    "Ändert oder ergänzt einen einzelnen Tag im Trainingsplan (der ganze Tag wird ersetzt). "
    "Vorher mit trainingsplan_abfragen den aktuellen Stand holen.",
    obj({"tag": PLAN_DAY}, ["tag"]),
)
async def trainingsplan_tag_aendern(ctx: ToolContext, args: dict) -> dict:
    days = await _load_plan(ctx)
    new = _clean(args["tag"])
    for i, d in enumerate(days):
        if d["tag"].strip().lower() == new["tag"].strip().lower():
            days[i] = new
            break
    else:
        days.append(new)
    await _save_plan(ctx, days)
    return {"gespeichert": True, "tag": new["tag"]}


@tool(
    "trainingsplan_abfragen",
    "Gibt den Wochen-Trainingsplan zurück (z. B. um zu wissen, was heute dran ist, oder um "
    "ein erledigtes Plan-Training mit training_speichern einzutragen).",
    obj({}),
)
async def trainingsplan_abfragen(ctx: ToolContext, args: dict) -> dict:
    return {"heute": WEEKDAYS[ctx.now.weekday()], "tage": await _load_plan(ctx)}
