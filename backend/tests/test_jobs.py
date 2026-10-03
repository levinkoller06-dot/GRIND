import asyncio
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import httpx

from app import jobs
from app.config import Settings
from app.db import ServiceDb
from app.tools.base import ToolContext
from app.tools.erinnerungen import erinnerung_setzen
from tests.fakes import FakeDb

TZ = ZoneInfo("Europe/Zurich")
# Samstag, 3. Oktober 2026, 07:00 in Zürich
NOW = datetime(2026, 10, 3, 7, 0, tzinfo=TZ).astimezone(UTC)


def run(coro):
    return asyncio.run(coro)


def test_secret_key_abfragen_sind_auf_nutzer_beschraenkt():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=[{"id": "x"}])

    settings = Settings(supabase_url="https://p.supabase.co", supabase_secret_key="sb_secret_abc")

    async def go():
        async with ServiceDb(settings) as service:
            service._http._transport = httpx.MockTransport(handler)
            db = service.for_user("user-1")
            await db.select("mail_accounts")
            await db.select("profiles", id="eq.user-2")  # fremde ID wird überschrieben
            await db.update("reminders", {"done_at": "x"}, id="eq.r1")
            await db.delete("notifications", user_id="eq.user-2")
            await db.insert("notifications", {"user_id": "user-2", "kind": "mail", "title": "t"})

    run(go())
    params = [dict(r.url.params) for r in seen]
    assert params[0]["user_id"] == "eq.user-1"
    assert params[1]["id"] == "eq.user-1"
    assert params[2]["user_id"] == "eq.user-1" and params[2]["id"] == "eq.r1"
    assert params[3]["user_id"] == "eq.user-1"
    assert b'"user_id":"user-1"' in seen[4].content.replace(b" ", b"")
    # Neuer Secret Key nur als apikey, nicht als Bearer-Token
    assert seen[0].headers["apikey"] == "sb_secret_abc"
    assert "authorization" not in seen[0].headers


def test_faellige_erinnerung_wird_einmal_gemeldet():
    db = FakeDb()
    db.tables["reminders"] = [
        {"id": "r1", "text": "Sporttasche", "due_at": (NOW - timedelta(minutes=1)).isoformat()},
        {"id": "r2", "text": "Später", "due_at": (NOW + timedelta(hours=1)).isoformat()},
    ]
    assert run(jobs.due_reminders(db, NOW)) == 1
    assert run(jobs.due_reminders(db, NOW)) == 0
    [note] = db.tables["notifications"]
    assert note["title"] == "⏰ Sporttasche" and note["kind"] == "erinnerung"
    assert db.tables["reminders"][1].get("done_at") is None


def test_morgen_check_inhalt_und_nur_einmal_pro_tag():
    db = FakeDb()
    today = datetime(2026, 10, 3, tzinfo=TZ)
    db.tables["events"] = [
        {"title": "Zahnarzt", "starts_at": today.replace(hour=14).isoformat(), "all_day": False, "kind": "termin"},
        {"title": "Abgabe Physik", "starts_at": (today + timedelta(days=2)).isoformat(), "all_day": True, "kind": "test"},
    ]  # fmt: skip
    db.tables["subjects"] = [{"id": "s1", "name": "Mathe"}]
    db.tables["exams"] = [
        {"date": "2026-10-04", "subject_id": "s1"},
        {"date": "2026-10-30", "subject_id": "s1"},  # zu weit weg
    ]
    db.tables["training_plans"] = [
        {"days": [{"tag": "Samstag oder Sonntag", "titel": "Beine", "uebungen": []}]}
    ]
    db.tables["pending_actions"] = [{"id": "p1", "status": "open"}]

    title, body = run(jobs.morning_summary(db, TZ, NOW))
    assert title == "☀️ Guten Morgen – Samstag, 3. Oktober"
    assert "14:00 Zahnarzt" in body
    assert "morgen: Mathe" in body and "Montag, 5. Oktober: Abgabe Physik" in body
    assert "30" not in body
    assert "💪 Training: Beine" in body
    assert "1 Vorschlag" in body

    run(jobs.morning_check(db, TZ, NOW))
    run(jobs.morning_check(db, TZ, NOW))
    assert len(db.tables["notifications"]) == 1


def test_morgen_check_zeitfenster():
    profile = {"morning_check_time": "06:30:00"}
    at = lambda h, m: datetime(2026, 10, 3, h, m, tzinfo=TZ)
    assert not jobs._morning_due(profile, at(6, 0))
    assert jobs._morning_due(profile, at(6, 30))
    assert not jobs._morning_due(profile, at(13, 0))
    assert not jobs._morning_due({"morning_check_time": None}, at(7, 0))


def mail(i, datum, **extra):
    return {
        "id": f"a:{i}",
        "von": {"name": f"Person {i}", "email": f"p{i}@x.ch"},
        "betreff": f"Betreff {i}",
        "datum": datum.isoformat(),
        "gelesen": False,
    } | extra


def test_neue_mails_werden_gemeldet(monkeypatch):
    db = FakeDb()
    db.tables["mail_accounts"] = [{"id": "a", "user_id": "user-1"}]
    db.tables["profiles"] = [{"id": "user-1"}]
    before = NOW - timedelta(hours=1)
    box = {
        "mails": [
            mail(1, NOW, antwort_noetig=True),
            mail(2, NOW, kategorie="werbung"),
            mail(3, NOW, gelesen=True),
            mail(4, before - timedelta(hours=1)),
        ]
    }

    async def fake_inbox(*_, **__):
        return box

    monkeypatch.setattr(jobs.mail_service, "inbox", fake_inbox)

    # Erster Abruf: nur merken, nichts melden
    assert run(jobs.check_mails(db, {}, before)) == 0
    assert run(jobs.check_mails(db, {"mail_checked_at": before.isoformat()}, NOW)) == 1
    [note] = db.tables["notifications"]
    assert note["title"] == "📬 1 neue Mail"
    assert "Person 1: Betreff 1 ↩ Antwort nötig" in note["body"]


def test_erinnerung_per_chat():
    db = FakeDb()
    ctx = ToolContext(db=db, tz=TZ, now=NOW.astimezone(TZ))
    res = run(erinnerung_setzen(ctx, {"text": "Ofen", "in_minuten": 20}))
    assert res["wann"] == "2026-10-03 07:20"
    res = run(erinnerung_setzen(ctx, {"text": "Gestern", "datum": "2026-10-02"}))
    assert "fehler" in res
    assert len(db.tables["reminders"]) == 1
