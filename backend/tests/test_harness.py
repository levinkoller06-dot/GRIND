import asyncio
from zoneinfo import ZoneInfo

import pytest

from app import actions, harness
from app.tools.kalender import event_times
from tests.fakes import FakeDb, FakeLlm, calls, text

TZ = ZoneInfo("Europe/Berlin")


def run(coro):
    return asyncio.run(coro)


def test_mehrere_dinge_in_einer_nachricht():
    db = FakeDb()
    llm = FakeLlm(
        calls(
            ("note_eintragen", {"fach": "Englisch", "note": 2}),
            ("test_anlegen", {"fach": "Mathe", "datum": "2026-10-01"}),
        ),
        text("Note gespeichert und Mathe-Test zum Bestätigen hingelegt."),
    )

    result = run(harness.chat(db, llm, "Hab ne 2 in Englisch und Donnerstag ist Mathetest"))

    assert result["tools"] == ["note_eintragen", "test_anlegen"]
    assert result["reply"].startswith("Note gespeichert")
    assert {s["name"] for s in db.tables["subjects"]} == {"Englisch", "Mathe"}
    assert db.tables["grades"][0]["value"] == 2
    assert len(db.tables["exams"]) == 1
    # Termin nur vorgeschlagen, nicht eingetragen
    assert "events" not in db.tables
    assert result["pending"][0]["kind"] == "event.create"
    assert result["pending"][0]["payload"]["titel"] == "Mathe-Test"
    # Tool-Ergebnisse gehen an die KI zurück
    last_request = llm.requests[1]
    assert "functionResponse" in last_request[-1]["parts"][0]
    # Verlauf und Protokoll gespeichert
    assert [m["role"] for m in db.tables["chat_messages"]] == ["user", "assistant"]
    assert len(db.tables["tool_log"]) == 2


def test_tool_fehler_wird_an_ki_gemeldet():
    db = FakeDb()
    llm = FakeLlm(
        calls(("termin_vorschlagen", {"titel": "Zahnarzt", "datum": "nächste Woche"})),
        text("Welches Datum genau?"),
    )
    result = run(harness.chat(db, llm, "Zahnarzt nächste Woche"))

    response = llm.requests[1][-1]["parts"][0]["functionResponse"]["response"]
    assert "fehler" in response
    assert db.tables["tool_log"][0]["ok"] is False
    assert result["pending"] == []


def test_fach_wird_wiederverwendet():
    db = FakeDb()
    for note in (2, 4):
        run(
            harness.chat(
                db,
                FakeLlm(calls(("note_eintragen", {"fach": "mathe", "note": note})), text("ok")),
                "x",
            )
        )
    assert len(db.tables["subjects"]) == 1
    assert db.tables["tool_log"][1]["result"]["neuer_schnitt"] == 3


def test_tageslimit():
    db = FakeDb()
    db.tables["profiles"] = [{"id": "user-1", "ai_daily_limit": 1}]
    run(harness.chat(db, FakeLlm(text("hi")), "hallo"))
    with pytest.raises(harness.LimitReached):
        run(harness.chat(db, FakeLlm(text("hi")), "nochmal"))


def test_event_times():
    start, end, all_day = event_times({"datum": "2026-10-01"}, TZ)
    assert all_day and end is None and start.hour == 0

    start, end, all_day = event_times(
        {"datum": "2026-10-01", "uhrzeit": "15:00", "ende_uhrzeit": "16:30"}, TZ
    )
    assert not all_day and start.isoformat() == "2026-10-01T15:00:00+02:00"
    assert (end - start).seconds == 90 * 60


def test_bestaetigen_mit_aenderung():
    db = FakeDb()
    llm = FakeLlm(
        calls(("termin_vorschlagen", {"titel": "Zahnarzt", "datum": "2026-10-02"})), text("ok")
    )
    pending = run(harness.chat(db, llm, "Zahnarzt Freitag"))["pending"][0]

    result = run(actions.decide(db, pending["id"], True, {"uhrzeit": "09:30"}, TZ))

    assert result["status"] == "confirmed"
    event = db.tables["events"][0]
    assert event["title"] == "Zahnarzt"
    assert event["starts_at"] == "2026-10-02T09:30:00+02:00"
    assert db.tables["pending_actions"][0]["status"] == "confirmed"
    with pytest.raises(actions.ActionError):
        run(actions.decide(db, pending["id"], True, {}, TZ))


def test_ablehnen():
    db = FakeDb()
    llm = FakeLlm(
        calls(("termin_vorschlagen", {"titel": "Kino", "datum": "2026-10-03"})), text("ok")
    )
    pending = run(harness.chat(db, llm, "Kino Samstag"))["pending"][0]
    run(actions.decide(db, pending["id"], False, {}, TZ))
    assert db.tables["pending_actions"][0]["status"] == "rejected"
    assert "events" not in db.tables


def test_ort_und_personen():
    db = FakeDb()
    llm = FakeLlm(
        calls(
            (
                "termin_vorschlagen",
                {"titel": "Kino", "datum": "2026-10-03", "ort": "Pathé", "mit": ["Tim", "Lea"]},
            )
        ),
        text("ok"),
    )
    pending = run(harness.chat(db, llm, "Samstag Kino mit Tim und Lea im Pathé"))["pending"][0]
    run(actions.decide(db, pending["id"], True, {"mit": ["Tim"]}, TZ))
    event = db.tables["events"][0]
    assert event["location"] == "Pathé"
    assert event["participants"] == ["Tim"]


def test_notenskala_im_prompt():
    from datetime import datetime

    now = datetime(2026, 9, 27, 12, tzinfo=TZ)
    assert "6 ist die beste" in harness.system_prompt(now, None, "ch")
    assert "1 ist die beste" in harness.system_prompt(now, None, "de")


def test_bewertung_je_nach_skala():
    from app.tools.noten import rating

    assert rating(6, "ch") == "sehr gut"
    assert rating(4, "ch") == "genügend (bestanden)"
    assert rating(3, "ch") == "ungenügend"
    assert rating(1, "de") == "sehr gut"
    assert rating(6, "de") == "schlecht"


def test_note_liefert_bewertung():
    db = FakeDb()
    llm = FakeLlm(calls(("note_eintragen", {"fach": "Englisch", "note": 6})), text("Stark!"))
    run(harness.chat(db, llm, "6 in Englisch"))
    result = db.tables["tool_log"][0]["result"]
    assert result["bewertung"] == "sehr gut"


def test_db_fehler_verstaendlich():
    from fastapi.testclient import TestClient

    from app.auth import get_current_user
    from app.db import DbError
    from app.main import app, get_db
    from tests.fakes import FakeUser

    class BrokenDb(FakeDb):
        async def select(self, table, **params):
            raise DbError('404: {"code":"PGRST205"}')

    async def broken():
        yield BrokenDb()

    app.dependency_overrides[get_db] = broken
    app.dependency_overrides[get_current_user] = FakeUser
    try:
        res = TestClient(app).get("/pending", headers={"Origin": "http://localhost:3000"})
    finally:
        app.dependency_overrides.clear()
    assert res.status_code == 500
    assert "SQL" in res.json()["detail"]
    assert res.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_termin_loeschen_nur_mit_bestaetigung():
    db = FakeDb()
    db.tables["exams"] = [{"id": "ex-1"}]
    db.tables["events"] = [
        {
            "id": "ev-1",
            "title": "Mathe-Test",
            "starts_at": "2026-10-01T00:00:00+02:00",
            "all_day": True,
            "kind": "test",
            "exam_id": "ex-1",
        }
    ]
    llm = FakeLlm(calls(("termin_loeschen", {"id": "ev-1"})), text("Zum Löschen hingelegt."))
    pending = run(harness.chat(db, llm, "Lösch den Mathetest"))["pending"][0]

    assert pending["kind"] == "event.delete"
    assert pending["payload"]["datum"] == "2026-10-01"
    assert len(db.tables["events"]) == 1  # noch nicht gelöscht

    run(actions.decide(db, pending["id"], True, {}, TZ))
    assert db.tables["events"] == []
    assert db.tables["exams"] == []


def test_note_loeschen():
    db = FakeDb()
    llm = FakeLlm(calls(("note_eintragen", {"fach": "Mathe", "note": 4})), text("ok"))
    run(harness.chat(db, llm, "4 in Mathe"))
    grade_id = db.tables["grades"][0]["id"]

    llm = FakeLlm(calls(("note_loeschen", {"id": grade_id})), text("Gelöscht."))
    run(harness.chat(db, llm, "Lösch die 4 in Mathe"))
    assert db.tables["grades"] == []


def test_modell_kette_bei_aufgebrauchtem_kontingent(monkeypatch):
    import httpx

    from app import llm as llm_module

    calls_made = []

    async def fake_post(self, url, json=None, headers=None, timeout=None):
        model = url.split("/models/")[1].split(":")[0]
        calls_made.append(model)
        request = httpx.Request("POST", url)
        if model == "a":
            return httpx.Response(
                429, text='{"quotaId": "RequestsPerDayPerProject"}', request=request
            )
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"role": "model", "parts": [{"text": "hi"}]}}]},
            request=request,
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    llm_module._exhausted.clear()
    gemini = llm_module.Gemini("key", ["a", "b"])

    assert run(gemini.generate("s", [], []))["parts"][0]["text"] == "hi"
    assert calls_made == ["a", "b"]
    # "a" ist jetzt für heute gesperrt und wird übersprungen
    run(gemini.generate("s", [], []))
    assert calls_made == ["a", "b", "b"]
    llm_module._exhausted.clear()


def test_alle_modelle_aufgebraucht(monkeypatch):
    import httpx

    from app import llm as llm_module

    async def fake_post(self, url, json=None, headers=None, timeout=None):
        return httpx.Response(429, text="PerDay", request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    llm_module._exhausted.clear()
    with pytest.raises(llm_module.LlmError, match="aufgebraucht"):
        run(llm_module.Gemini("key", ["a", "b"]).generate("s", [], []))
    llm_module._exhausted.clear()


def test_termin_ohne_bestaetigung_direkt_eingetragen(monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "confirm_actions", False)
    db = FakeDb()
    llm = FakeLlm(
        calls(
            ("termin_vorschlagen", {"titel": "Zahnarzt", "datum": "2026-10-02", "uhrzeit": "15:00"})
        ),
        text("Eingetragen!"),
    )
    result = run(harness.chat(db, llm, "Morgen 15 Uhr Zahnarzt"))
    assert result["pending"] == []
    assert db.tables["events"][0]["title"] == "Zahnarzt"
    assert "ohne nachzufragen" in harness.actions_rule()
