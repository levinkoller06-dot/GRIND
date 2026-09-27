"""Essensvorschläge für den Rest des Tages (Ernährung-Tab)."""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.db import Db
from app.llm import Gemini
from app.tools.essen import totals
from app.tools.gym import WEEKDAYS

SCHEMA = {
    "type": "object",
    "properties": {
        "vorschlaege": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "uhrzeit": {"type": "string", "description": "HH:MM"},
                    "essen": {"type": "string"},
                    "kcal": {"type": "number"},
                    "protein_g": {"type": "number"},
                    "grund": {"type": "string", "description": "sehr kurz, max. 6 Wörter"},
                },
                "required": ["uhrzeit", "essen", "kcal", "protein_g"],
            },
        },
        "hinweis": {"type": "string", "description": "ein kurzer Satz"},
    },
    "required": ["vorschlaege"],
}

SYSTEM = """Du bist Ernährungs-Coach in der App GRIND (Schüler, macht Krafttraining).
Plane die restlichen Mahlzeiten/Snacks des Tages, damit die Tagesziele möglichst genau erreicht
werden. Einfache, alltagstaugliche Sachen (Apfel, Proteinshake, Quark, Brot mit Käse, Nudeln …).
Nur Uhrzeiten nach der aktuellen Uhrzeit, höchstens 4 Vorschläge, letzte spätestens 21:30.
Sind die Ziele schon erreicht: keine oder nur leichte Vorschläge und das im Hinweis sagen.
Deutsch, kurz."""

# Einfacher Cache pro Nutzer: gleiche Lage → gleiche Vorschläge, spart API-Aufrufe
_cache: dict[str, tuple[tuple, dict]] = {}


async def suggestions(db: Db, llm: Gemini, tz: ZoneInfo) -> dict:
    now = datetime.now(tz)
    today = now.date()
    start = datetime.combine(today, time.min, tz)

    meals = await db.select(
        "meals",
        select="description,eaten_at,meal_items(name,kcal,protein_g,carbs_g,fat_g)",
        eaten_at=f"gte.{start.isoformat()}",
        order="eaten_at",
        **{"and": f"(eaten_at.lt.{(start + timedelta(days=1)).isoformat()})"},
    )
    profiles = await db.select("profiles", select="goal_kcal,goal_protein_g", id=f"eq.{db.user.id}")
    goals = profiles[0] if profiles else {}
    plan = await db.select("training_plans", select="days", user_id=f"eq.{db.user.id}")
    today_plan = _plan_for(plan[0]["days"] if plan else [], today)

    eaten = totals([i for m in meals for i in m["meal_items"]])
    key = (
        db.user.id,
        today,
        round(eaten["kcal"]),
        now.hour,
        goals.get("goal_kcal"),
        goals.get("goal_protein_g"),
    )
    cached = _cache.get(db.user.id)
    if cached and cached[0] == key:
        return cached[1]

    if not goals.get("goal_kcal") and not goals.get("goal_protein_g"):
        return {
            "vorschlaege": [],
            "hinweis": "Setz zuerst deine Ziele (Kalorien/Protein).",
            "gegessen": eaten,
        }

    eaten_list = (
        "\n".join(
            f"- {datetime.fromisoformat(m['eaten_at']).astimezone(tz):%H:%M} "
            f"{m['description'] or ', '.join(i['name'] for i in m['meal_items'])}"
            for m in meals
        )
        or "- noch nichts"
    )
    prompt = f"""Jetzt: {WEEKDAYS[now.weekday()]} {now:%H:%M}
Ziel: {goals.get("goal_kcal") or "?"} kcal, {goals.get("goal_protein_g") or "?"} g Protein
Bisher gegessen: {eaten["kcal"]:.0f} kcal, {eaten["protein_g"]:.0f} g Protein
{eaten_list}
Training heute: {today_plan or "keins geplant"}"""

    result = await llm.generate_json(SYSTEM, prompt, SCHEMA)
    result["gegessen"] = eaten
    _cache[db.user.id] = (key, result)
    return result


def _plan_for(days: list[dict], today: date) -> str | None:
    name = WEEKDAYS[today.weekday()].lower()
    for d in days:
        if name in d.get("tag", "").lower():
            return "Pause" if d.get("pause") else d.get("titel")
    return None
