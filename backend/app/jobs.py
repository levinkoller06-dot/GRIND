"""Zeitplan: Morgen-Check, Erinnerungen und Mail-Abruf.

Läuft im Backend als Hintergrund-Schleife – normaler Code, keine KI (bis auf die
Mail-Einordnung durch Jev, die beim Abruf sowieso passiert). Ergebnisse landen als
Meldung in `notifications` und erscheinen im Gehirn-Tab.
"""

import asyncio
import logging
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app import moodle
from app.config import Settings
from app.db import Db, DbError, ServiceDb
from app.mail import service as mail_service
from app.tools.gym import WEEKDAYS

log = logging.getLogger(__name__)

MONTHS = [
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
]  # fmt: skip

# Nach dieser Uhrzeit kommt kein Morgen-Check mehr (Backend erst nachmittags gestartet)
MORNING_UNTIL = time(12, 0)
TEST_DAYS = 7

# Letzter Mail-Abruf pro Nutzer (nur im Speicher, damit nicht jede Minute abgerufen wird)
_last_mail_check: dict[str, datetime] = {}


def _ts(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _day_label(day: date) -> str:
    return f"{WEEKDAYS[day.weekday()]}, {day.day}. {MONTHS[day.month - 1]}"


async def notify(
    db: Db,
    kind: str,
    title: str,
    body: str | None = None,
    link: str | None = None,
    key: str | None = None,
) -> dict | None:
    """Legt eine Meldung an. Mit `key` höchstens einmal (z. B. ein Morgen-Check pro Tag)."""
    if key and await db.select("notifications", select="id", key=f"eq.{key}"):
        return None
    row = {"kind": kind, "title": title, "body": body, "link": link, "key": key}
    try:
        return await db.insert("notifications", {"user_id": db.user.id, **row})
    except DbError as e:
        if "23505" in str(e):  # gleichzeitig schon angelegt
            return None
        raise


# ---------------------------------------------------------------------------
# Erinnerungen
# ---------------------------------------------------------------------------
async def due_reminders(db: Db, now: datetime) -> int:
    rows = await db.select(
        "reminders", done_at="is.null", due_at=f"lte.{now.isoformat()}", order="due_at"
    )
    rows = [r for r in rows if not r.get("done_at") and _ts(r["due_at"]) <= now]
    for r in rows:
        await notify(db, "erinnerung", f"⏰ {r['text']}", key=f"erinnerung:{r['id']}")
        await db.update("reminders", {"done_at": now.isoformat()}, id=f"eq.{r['id']}")
    return len(rows)


# ---------------------------------------------------------------------------
# Morgen-Check
# ---------------------------------------------------------------------------
def _clock(value: str, tz: ZoneInfo) -> str:
    return _ts(value).astimezone(tz).strftime("%H:%M")


async def morning_summary(db: Db, tz: ZoneInfo, now: datetime) -> tuple[str, str]:
    """Titel und Text des Morgen-Checks: Termine, Tests, Training, Erinnerungen, Vorschläge."""
    today = now.astimezone(tz).date()
    start = datetime.combine(today, time.min, tz)
    end = start + timedelta(days=1)
    test_end = start + timedelta(days=TEST_DAYS + 1)

    events, exams, subjects, plan, reminders, pending = await asyncio.gather(
        db.select(
            "events",
            select="title,starts_at,all_day,kind",
            starts_at=f"gte.{start.isoformat()}",
            **{"and": f"(starts_at.lt.{test_end.isoformat()})"},
            order="starts_at",
        ),
        db.select(
            "exams",
            select="date,subject_id,topics",
            date=f"gte.{today.isoformat()}",
            order="date",
        ),
        db.select("subjects", select="id,name"),
        db.select("training_plans", select="days"),
        db.select("reminders", select="text,due_at,done_at", done_at="is.null", order="due_at"),
        db.select("pending_actions", select="id", status="eq.open"),
    )

    lines: list[str] = []

    todays = [e for e in events if start <= _ts(e["starts_at"]) < end]
    if todays:
        lines.append("📅 Heute:")
        for e in todays:
            when = "ganztägig" if e["all_day"] else _clock(e["starts_at"], tz)
            lines.append(f"  • {when} {e['title']}")
    else:
        lines.append("📅 Heute keine Termine.")

    names = {s["id"]: s["name"] for s in subjects}
    tests = [
        (date.fromisoformat(x["date"]), names.get(x["subject_id"], "Test"))
        for x in exams
        if date.fromisoformat(x["date"]) <= today + timedelta(days=TEST_DAYS)
    ] + [
        (_ts(e["starts_at"]).astimezone(tz).date(), e["title"])
        for e in events
        if e["kind"] == "test" and _ts(e["starts_at"]) < test_end
    ]
    if tests:
        lines.append("📝 Tests in den nächsten Tagen:")
        for day, name in sorted(set(tests)):
            when = (
                "heute"
                if day == today
                else "morgen"
                if day == today + timedelta(1)
                else _day_label(day)
            )
            lines.append(f"  • {when}: {name}")

    days = plan[0]["days"] if plan else []
    weekday = WEEKDAYS[today.weekday()].lower()
    training = next((d for d in days if weekday in d["tag"].lower()), None)
    if training:
        lines.append(
            "😴 Training: Ruhetag" if training.get("pause") else f"💪 Training: {training['titel']}"
        )

    due_today = [r for r in reminders if not r.get("done_at") and _ts(r["due_at"]) < end]
    if due_today:
        lines.append("⏰ Erinnerungen heute:")
        lines += [f"  • {_clock(r['due_at'], tz)} {r['text']}" for r in due_today]

    if pending:
        lines.append(f"✋ {len(pending)} Vorschlag/Vorschläge warten auf deine Bestätigung.")

    return f"☀️ Guten Morgen – {_day_label(today)}", "\n".join(lines)


def _morning_due(profile: dict, local_now: datetime) -> bool:
    at = profile.get("morning_check_time")
    if not at:
        return False
    return time.fromisoformat(at) <= local_now.time() < MORNING_UNTIL


async def morning_check(db: Db, tz: ZoneInfo, now: datetime, force: bool = False) -> dict | None:
    today = now.astimezone(tz).date()
    title, body = await morning_summary(db, tz, now)
    # Mit force (Knopf "Jetzt testen") ohne key, damit es beliebig oft geht
    return await notify(db, "morgen", title, body, "/", None if force else f"morgen:{today}")


# ---------------------------------------------------------------------------
# Mail-Abruf
# ---------------------------------------------------------------------------
async def check_mails(db: Db, profile: dict, now: datetime) -> int:
    """Ruft die Postfächer ab (Werbung wird dabei aussortiert) und meldet neue Mails."""
    if not await db.select("mail_accounts", select="id", limit="1"):
        return 0
    since = profile.get("mail_checked_at")
    box = await mail_service.inbox(db, days=2, limit=30)
    await db.update("profiles", {"mail_checked_at": now.isoformat()}, id=f"eq.{db.user.id}")
    if not since:
        return 0  # erster Abruf: alles bisherige gilt als bekannt
    new = [
        m
        for m in box["mails"]
        if m.get("datum")
        and _ts(m["datum"]) > _ts(since)
        and not m.get("gelesen")
        and m.get("kategorie") != "werbung"
    ]
    if not new:
        return 0
    lines = [
        f"• {m['von']['name'] or m['von']['email']}: {m['betreff']}"
        + (" ↩ Antwort nötig" if m.get("antwort_noetig") else "")
        for m in new[:5]
    ]
    if len(new) > 5:
        lines.append(f"… und {len(new) - 5} weitere")
    title = "📬 1 neue Mail" if len(new) == 1 else f"📬 {len(new)} neue Mails"
    await notify(db, "mail", title, "\n".join(lines), "/mails", f"mail:{now.isoformat()}")
    return len(new)


# ---------------------------------------------------------------------------
# Schleife
# ---------------------------------------------------------------------------
async def run_user(db: Db, profile: dict, now: datetime, settings: Settings) -> None:
    tz = ZoneInfo(profile.get("timezone") or "Europe/Berlin")
    await due_reminders(db, now)

    last = _last_mail_check.get(db.user.id)
    if not last or now - last >= timedelta(minutes=settings.mail_check_min):
        _last_mail_check[db.user.id] = now
        # Moodle zuerst, damit neue Prüfungen schon im Morgen-Check stehen
        for job in (moodle.sync(db), check_mails(db, profile, now)):
            try:
                await job
            except Exception as e:  # noqa: BLE001 – ein kaputtes Postfach soll den Rest nicht stoppen
                log.warning("Hintergrund-Abruf für %s fehlgeschlagen: %s", db.user.id, e)

    if _morning_due(profile, now.astimezone(tz)):
        await morning_check(db, tz, now)


async def tick(service: ServiceDb, settings: Settings, now: datetime) -> None:
    profiles = await service.select(
        "profiles", select="id,timezone,morning_check_time,mail_checked_at"
    )
    for profile in profiles:
        try:
            await run_user(service.for_user(profile["id"]), profile, now, settings)
        except Exception:
            log.exception("Zeitplan für Nutzer %s fehlgeschlagen", profile["id"])


async def run_forever(settings: Settings) -> None:
    log.info(
        "Zeitplan läuft (alle %d s, Mails alle %d min)",
        settings.jobs_interval_s,
        settings.mail_check_min,
    )
    async with ServiceDb(settings) as service:
        while True:
            try:
                await tick(service, settings, datetime.now(UTC))
            except DbError as e:  # z. B. Migration fehlt oder falscher Key – ohne Traceback-Flut
                log.warning("Zeitplan: Datenbank-Fehler: %s", e)
            except Exception:
                log.exception("Zeitplan-Durchlauf fehlgeschlagen")
            await asyncio.sleep(settings.jobs_interval_s)
