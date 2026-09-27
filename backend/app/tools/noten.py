from datetime import date

from app.tools.base import ToolContext, obj, propose, tool
from app.tools.kalender import describe


def _norm(s: str) -> str:
    return " ".join(s.lower().split())


def match_subject(subjects: list[dict], name: str) -> dict | None:
    """Findet ein Fach über den Namen oder einen Alias (Groß-/Kleinschreibung egal)."""
    wanted = _norm(name)
    for s in subjects:
        if _norm(s["name"]) == wanted or wanted in (_norm(a) for a in s.get("aliases") or []):
            return s
    return None


async def find_subject(ctx: ToolContext, name: str) -> dict | None:
    return match_subject(await ctx.db.select("subjects"), name)


async def get_or_create_subject(ctx: ToolContext, name: str) -> dict:
    found = await find_subject(ctx, name)
    if found:
        return found
    return await ctx.db.insert("subjects", {"user_id": ctx.db.user.id, "name": name.strip()})


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
    "Speichert eine Note in einem Fach. Nutze den exakten Namen eines bestehenden Fachs "
    "(siehe Fächerliste). Nur wenn es das Fach wirklich nicht gibt, wird es neu angelegt.",
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
    subjects = await ctx.db.select(
        "subjects", select="id,name,aliases,grades(id,value,weight,kind,date,note)"
    )
    if args.get("fach"):
        found = match_subject(subjects, args["fach"])
        subjects = [found] if found else []
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


@tool(
    "note_loeschen",
    "Löscht eine Note (z. B. falsch eingetragen). Die ID vorher mit noten_abfragen herausfinden. "
    "Bei mehreren passenden Noten nachfragen, welche gemeint ist.",
    obj({"id": {"type": "string", "description": "ID der Note aus noten_abfragen"}}, ["id"]),
)
async def note_loeschen(ctx: ToolContext, args: dict) -> dict:
    rows = await ctx.db.select("grades", id=f"eq.{args['id']}")
    if not rows:
        raise ValueError("Note nicht gefunden – erst noten_abfragen aufrufen")
    await ctx.db.delete("grades", id=f"eq.{args['id']}")
    return {"geloescht": True, "note": rows[0]["value"]}


@tool(
    "faecher_anlegen",
    "Legt ein oder mehrere Schulfächer an (z. B. aus dem Stundenplan). Aliase sind weitere "
    "Namen, unter denen das Fach auch gemeint sein kann.",
    obj(
        {
            "faecher": {
                "type": "array",
                "items": obj(
                    {
                        "name": {"type": "string", "description": "z. B. 'ABU', 'Modul 114'"},
                        "aliase": {"type": "array", "items": {"type": "string"}},
                    },
                    ["name"],
                ),
            }
        },
        ["faecher"],
    ),
)
async def faecher_anlegen(ctx: ToolContext, args: dict) -> dict:
    existing = await ctx.db.select("subjects")
    created, skipped = [], []
    for f in args["faecher"]:
        if match_subject(existing, f["name"]):
            skipped.append(f["name"])
            continue
        row = await ctx.db.insert(
            "subjects",
            {
                "user_id": ctx.db.user.id,
                "name": f["name"].strip(),
                "aliases": f.get("aliase") or [],
            },
        )
        existing.append(row)
        created.append(row["name"])
    return {"angelegt": created, "gab_es_schon": skipped}


@tool(
    "fach_aendern",
    "Benennt ein Fach um und/oder setzt seine Aliase neu.",
    obj(
        {
            "fach": {"type": "string", "description": "Aktueller Name oder Alias"},
            "neuer_name": {"type": "string"},
            "aliase": {"type": "array", "items": {"type": "string"}},
        },
        ["fach"],
    ),
)
async def fach_aendern(ctx: ToolContext, args: dict) -> dict:
    subject = await find_subject(ctx, args["fach"])
    if not subject:
        raise ValueError(f"Fach '{args['fach']}' gibt es nicht")
    values = {}
    if args.get("neuer_name"):
        values["name"] = args["neuer_name"].strip()
    if args.get("aliase") is not None:
        values["aliases"] = args["aliase"]
    if not values:
        raise ValueError("Nichts zu ändern")
    await ctx.db.update("subjects", values, id=f"eq.{subject['id']}")
    return {"geaendert": True, **values}


@tool(
    "fach_loeschen",
    "Löscht ein Fach. Geht nur, wenn es keine Noten mehr hat (sonst erst die Noten löschen).",
    obj({"fach": {"type": "string"}}, ["fach"]),
)
async def fach_loeschen(ctx: ToolContext, args: dict) -> dict:
    subject = await find_subject(ctx, args["fach"])
    if not subject:
        raise ValueError(f"Fach '{args['fach']}' gibt es nicht")
    grades = await ctx.db.select("grades", select="id", subject_id=f"eq.{subject['id']}")
    if grades:
        raise ValueError(
            f"{subject['name']} hat noch {len(grades)} Note(n). Frag den Nutzer, "
            "ob die Noten wirklich gelöscht werden sollen."
        )
    await ctx.db.delete("subjects", id=f"eq.{subject['id']}")
    return {"geloescht": subject["name"]}
