import asyncio
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from cryptography.fernet import Fernet

from app import moodle
from app.config import get_settings
from app.mail.crypto import encrypt
from tests.fakes import FakeDb

TZ = ZoneInfo("Europe/Zurich")


def ics(*events: str) -> str:
    return "BEGIN:VCALENDAR\r\nVERSION:2.0\r\n" + "".join(events) + "END:VCALENDAR\r\n"


def vevent(uid: str, summary: str, start: str, category: str = "M117-TI26aef") -> str:
    return (
        f"BEGIN:VEVENT\r\nUID:{uid}@moodle.bzu.ch\r\nSUMMARY:{summary}\r\n"
        f"DTSTART:{start}\r\nDTEND:{start}\r\nCATEGORIES:{category}\r\nEND:VEVENT\r\n"
    )


def stamp(days: int, hour: int = 21, minute: int = 59) -> str:
    d = (datetime.now(UTC) + timedelta(days=days)).replace(hour=hour, minute=minute, second=0)
    return d.strftime("%Y%m%dT%H%M%SZ")


def test_ics_parsen_mit_umbruch_und_escapes():
    text = ics(
        "BEGIN:VEVENT\r\nUID:1@m\r\nSUMMARY:Prüfung 1 (ohne negative Zahlen\\, Kombi\r\n natorik) - TIf beginnt\r\n"
        "DTSTART:20261001T120500Z\r\nEND:VEVENT\r\n"
    )
    [event] = moodle.parse_ics(text)
    assert event["SUMMARY"] == "Prüfung 1 (ohne negative Zahlen, Kombinatorik) - TIf beginnt"


def test_abgaben_und_pruefungen_einordnen():
    due = moodle.to_event(
        {
            "UID": "1",
            "SUMMARY": "Simulation mit Filius ist fällig.",
            "DTSTART": "20261018T215900Z",
            "CATEGORIES": "M117-TI26aef",
        },
        TZ,
    )
    # 21:59 UTC = 23:59 in Zürich → ganztägig am 18.10.
    assert due["title"] == "📚 Simulation mit Filius" and due["all_day"] and due["kind"] == "schule"
    assert due["starts_at"].startswith("2026-10-18T00:00:00")
    assert due["notes"] == "Moodle · M117-TI26aef"

    exam = moodle.to_event(
        {"UID": "2", "SUMMARY": "Prüfung 1 - TIf beginnt", "DTSTART": "20261001T120500Z"}, TZ
    )
    assert exam["title"] == "Prüfung 1 - TIf" and exam["kind"] == "test" and not exam["all_day"]
    assert moodle.to_event({"SUMMARY": "ohne UID"}, TZ) is None


def test_abgleich_neu_geaendert_entfernt(monkeypatch):
    monkeypatch.setattr(get_settings(), "encryption_key", Fernet.generate_key().decode())
    db = FakeDb()
    db.tables["profiles"] = [
        {
            "id": "user-1",
            "timezone": "Europe/Zurich",
            "moodle_ical_enc": encrypt("https://moodle.bzu.ch/x"),
            "moodle_synced_at": None,
        }
    ]
    feed = [
        ics(
            vevent("1", "Aufgabe A ist fällig.", stamp(3)),
            vevent("2", "Test in Recht", stamp(5, 9, 1)),
        )
    ]

    async def fake_download(url):
        assert url == "https://moodle.bzu.ch/x"
        return moodle.parse_ics(feed[0])

    monkeypatch.setattr(moodle, "_download", fake_download)
    result = asyncio.run(moodle.sync(db, force=True))
    assert result["neu"] == 2
    assert {e["title"] for e in db.tables["events"]} == {"📚 Aufgabe A", "Test in Recht"}

    # Gleich nochmal: nichts doppelt, und ohne force wird übersprungen
    assert asyncio.run(moodle.sync(db))["uebersprungen"]
    assert asyncio.run(moodle.sync(db, force=True))["neu"] == 0

    # Titel geändert, Aufgabe A in Moodle gelöscht
    feed[0] = ics(vevent("2", "Test in Rechtsgrundlagen", stamp(5, 9, 1)))
    result = asyncio.run(moodle.sync(db, force=True))
    assert (result["geaendert"], result["entfernt"]) == (1, 1)
    assert [e["title"] for e in db.tables["events"]] == ["Test in Rechtsgrundlagen"]

    asyncio.run(moodle.disconnect(db))
    assert db.tables["events"] == [] and db.tables["profiles"][0]["moodle_ical_enc"] is None


def test_ohne_link_nicht_verbunden():
    db = FakeDb()
    db.tables["profiles"] = [{"id": "user-1"}]
    assert asyncio.run(moodle.sync(db)) == {"verbunden": False}
