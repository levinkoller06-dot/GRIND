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


GRADE_SCALES = {
    "ch": "Schweizer Notenskala: 6 ist die beste Note, 5 gut, 4 genügend (knapp bestanden), "
    "unter 4 ungenügend, 1 die schlechteste. Eine 6 ist also super, eine 3 ist schlecht.",
    "de": "Deutsche Notenskala: 1 ist die beste Note, 2 gut, 3 befriedigend, 4 ausreichend, "
    "5 mangelhaft, 6 die schlechteste.",
}


def subject_list(subjects: list[dict]) -> str:
    if not subjects:
        return "(noch keine)"
    return ", ".join(
        s["name"] + (f" (auch: {', '.join(s['aliases'])})" if s.get("aliases") else "")
        for s in subjects
    )


def system_prompt(
    now: datetime, name: str | None, grade_scale: str = "ch", subjects: list[dict] | None = None
) -> str:
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

Noten: {GRADE_SCALES.get(grade_scale, GRADE_SCALES["ch"])}
Fächer des Nutzers: {subject_list(subjects or [])}
Ordne Noten und Tests immer einem dieser Fächer zu, auch bei Tippfehlern oder Englisch
(z. B. „english“ → Englisch, „Gesellschaft“ → ABU). Neue Fächer nur, wenn der Nutzer das will.
Bewerte Noten und Schnitte immer nach dieser Skala. Die Tools liefern eine „bewertung“ mit,
die stimmt immer – richte deine Reaktion danach (bei „sehr gut“ feiern, nie trösten).
Schreib keine Markdown-Tabellen oder Überschriften; **fett** ist ok.

Regeln:
- Eine Nachricht kann mehrere Dinge enthalten. Erledige alle mit den passenden Tools, gern mehrere Tools auf einmal.
- Termine werden nie direkt eingetragen, sondern nur vorgeschlagen. Der Nutzer bestätigt sie in der App.
  Sag also z. B. „Hab dir den Termin zum Bestätigen hingelegt“, nie „eingetragen“.
- Tests/Klassenarbeiten immer mit test_anlegen, nicht mit termin_vorschlagen.
- Bei Terminen Ort („ort“) und Personen („mit“) mitgeben, wenn der Nutzer sie nennt
  („Kino mit Tim und Lea im Pathé“ → mit: ["Tim", "Lea"], ort: "Pathé").
- Training: „3×10 Liegestütze“ → saetze 3, wiederholungen 10. Mehrere Übungen in ein Training.
  Neue Rekorde feiern!
- Essen: Nährwerte selbst realistisch schätzen und mit mahlzeit_eintragen speichern, nicht nachfragen,
  außer die Menge ist völlig unklar. Bei einem Foto: erkennen, was drauf ist, schätzen, eintragen
  (vom_foto: true). Danach kurz Kalorien/Protein nennen und wie weit es bis zum Tagesziel ist.
- Löschen: erst termine_abfragen bzw. noten_abfragen, um die ID zu finden, dann termin_loeschen
  (muss bestätigt werden) bzw. note_loeschen. Ist unklar, welcher Eintrag gemeint ist, kurz nachfragen.
- Trainingsplan: schickt der Nutzer seinen Plan, mit trainingsplan_setzen speichern (alle Tage;
  „-11“ hinter einer Übung = stufe „11“). Sagt er „Training von heute gemacht“, den Plan holen
  und die Übungen des heutigen Tages mit training_speichern eintragen.
- Mails: mails_abfragen durchsucht alle verbundenen Postfächer. Zum Antworten erst die Mail mit
  mail_lesen lesen, dann mail_senden mit antwort_auf_id. mail_senden verschickt nie direkt – der
  Nutzer bestätigt in der App. Schreib Mails im Stil des Nutzers (Deutsch, passende Anrede,
  Gruss mit seinem Namen), kurz und freundlich. Fasse Mails knapp zusammen statt sie abzuschreiben.
- Hat der Nutzer sich vertan („nee, das war gestern“), den falschen Eintrag mit eintrag_loeschen
  entfernen und neu eintragen.
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


async def chat(db: Db, llm: Gemini, message: str, image: dict | None = None) -> dict:
    """`image`: optionales Foto als {"mime_type": ..., "data": <base64>}."""
    profiles = await db.select("profiles", id=f"eq.{db.user.id}")
    profile = profiles[0] if profiles else {}
    tz = ZoneInfo(profile.get("timezone") or "Europe/Berlin")
    now = datetime.now(tz)

    await check_limit(db, now, profile.get("ai_daily_limit") or 100)

    contents = await load_history(db)
    parts: list[dict] = [{"text": message}]
    if image:
        parts.append({"inlineData": {"mimeType": image["mime_type"], "data": image["data"]}})
    contents.append({"role": "user", "parts": parts})
    # Fotos werden nicht gespeichert, im Verlauf steht nur ein Hinweis
    stored = f"📷 {message}" if image else message
    await db.insert("chat_messages", {"user_id": db.user.id, "role": "user", "content": stored})

    ctx = ToolContext(db=db, tz=tz, now=now, grade_scale=profile.get("grade_scale") or "ch")
    declarations = [t.declaration() for t in REGISTRY.values()]
    subjects = await db.select("subjects", order="name")
    system = system_prompt(
        now, profile.get("display_name"), profile.get("grade_scale") or "ch", subjects
    )
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
