from datetime import date

from app.tools.base import ToolContext, obj, propose, tool
from app.tools.kalender import describe


async def get_or_create_subject(ctx: ToolContext, name: str) -> dict:
    name = name.strip()
    found = await ctx.db.select("subjects", name=f"ilike.{name}", limit="1")
    if found:
        return found[0]
    return await ctx.db.insert("subjects", {"user_id": ctx.db.user.id, "name": name})


def rating(value: float | None, scale: str) -> str | None:
    """Bewertung einer Note in Worten, unabhängig von der Skala."""
    if value is None:
        return None
    points = float(value) if scale == "ch" else 7 - float(value)  # höher = besser
    if points >= 5.5:
        return "sehr gut"
    if points >= 4.75:
        return "gut"
    if points >= 4:
        return "genügend (bestanden)"
    if points >= 3:
        return "ungenügend"
    return "schlecht"


def average(grades: list[dict]) -> float | None:
    total_weight = sum(float(g["weight"]) for g in grades)
    if not total_weight:
        return None
    return round(sum(float(g["value"]) * float(g["weight"]) for g in grades) / total_weight, 2)


@tool(
    "note_eintragen",
    "Speichert eine Note in einem Fach. Das Fach wird angelegt, falls es noch nicht existiert.",
    obj(
        {
            "fach": {"type": "string", "description": "z. B. 'Mathe', 'Englisch'"},
            "note": {"type": "number", "description": "Die Note als Zahl, z. B. 2 oder 2.5"},
            "art": {"type": "string", "enum": ["test", "muendlich", "sonstiges"]},
            "gewichtung": {"type": "number", "description": "Standard 1"},
            "datum": {"type": "string", "description": "YYYY-MM-DD, Standard: heute"},
            "notiz": {"type": "string"},
        },
        ["fach", "note"],
    ),
)
async def note_eintragen(ctx: ToolContext, args: dict) -> dict:
    subject = await get_or_create_subject(ctx, args["fach"])
    grade = await ctx.db.insert(
        "grades",
        {
            "user_id": ctx.db.user.id,
            "subject_id": subject["id"],
            "value": args["note"],
            "kind": args.get("art") or "test",
            "weight": args.get("gewichtung") or 1,
            "date": args.get("datum") or ctx.now.date().isoformat(),
            "note": args.get("notiz"),
        },
    )
    grades = await ctx.db.select("grades", subject_id=f"eq.{subject['id']}")
    avg = average(grades)
    return {
        "gespeichert": True,
        "fach": subject["name"],
        "note": grade["value"],
        "bewertung": rating(grade["value"], ctx.grade_scale),
        "neuer_schnitt": avg,
        "bewertung_schnitt": rating(avg, ctx.grade_scale),
    }


@tool(
    "noten_abfragen",
    "Gibt Noten und Durchschnitt zurück, für ein Fach oder alle Fächer.",
    obj({"fach": {"type": "string", "description": "Optional, sonst alle Fächer"}}),
)
async def noten_abfragen(ctx: ToolContext, args: dict) -> dict:
    filters = {"name": f"ilike.{args['fach'].strip()}"} if args.get("fach") else {}
    subjects = await ctx.db.select(
        "subjects", select="name,grades(value,weight,kind,date)", **filters
    )
    return {
        "faecher": [
            {
                "fach": s["name"],
                "noten": s["grades"],
                "schnitt": average(s["grades"]),
                "bewertung_schnitt": rating(average(s["grades"]), ctx.grade_scale),
            }
            for s in subjects
        ]
    }


@tool(
    "test_anlegen",
    "Legt einen Test / eine Klassenarbeit an und schlägt den passenden Kalendertermin vor "
    "(der Termin muss vom Nutzer bestätigt werden).",
    obj(
        {
            "fach": {"type": "string"},
            "datum": {"type": "string", "description": "YYYY-MM-DD"},
            "themen": {"type": "string", "description": "Stoff / Themen, falls bekannt"},
            "uhrzeit": {"type": "string", "description": "HH:MM, falls bekannt"},
        },
        ["fach", "datum"],
    ),
)
async def test_anlegen(ctx: ToolContext, args: dict) -> dict:
    date.fromisoformat(args["datum"])
    subject = await get_or_create_subject(ctx, args["fach"])
    exam = await ctx.db.insert(
        "exams",
        {
            "user_id": ctx.db.user.id,
            "subject_id": subject["id"],
            "date": args["datum"],
            "topics": args.get("themen"),
        },
    )
    payload = {
        "titel": f"{subject['name']}-Test",
        "datum": args["datum"],
        "art": "test",
        "exam_id": exam["id"],
    }
    if args.get("uhrzeit"):
        payload["uhrzeit"] = args["uhrzeit"]
    if args.get("themen"):
        payload["notiz"] = args["themen"]
    result = await propose(ctx, "event.create", payload, describe(payload))
    return {"test_gespeichert": True, **result}
