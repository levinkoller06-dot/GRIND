import asyncio
from email.message import EmailMessage
from zoneinfo import ZoneInfo

import pytest
from cryptography.fernet import Fernet

from app import actions, harness
from app.config import get_settings
from app.mail import crypto, imap, service
from tests.fakes import FakeDb, FakeLlm, calls, text

TZ = ZoneInfo("Europe/Berlin")
ACC = imap.ImapAccount(
    id="acc-1",
    email="levin@hispeed.ch",
    password="x",
    imap_host="imap.hispeed.ch",
    imap_port=993,
    smtp_host="smtp.hispeed.ch",
    smtp_port=587,
    label="Privat",
)


def run(coro):
    return asyncio.run(coro)


def make_mail(html: bool = False) -> bytes:
    msg = EmailMessage()
    msg["From"] = "Tim Müller <tim@example.com>"
    msg["To"] = "levin@hispeed.ch"
    msg["Subject"] = "Kino am Samstag?"
    msg["Date"] = "Sun, 27 Sep 2026 10:15:00 +0200"
    msg["Message-ID"] = "<abc@example.com>"
    if html:
        msg.set_content(
            "<p>Hey Levin,</p><p>kommst du <b>Samstag</b> mit ins Kino?</p>", subtype="html"
        )
    else:
        msg.set_content("Hey Levin,\n\nkommst du Samstag mit ins Kino?\n\nTim")
    return msg.as_bytes()


def test_zusammenfassung_einer_mail():
    summary = imap._summary(ACC, "42", b"\\Seen", make_mail())
    assert summary["id"] == "acc-1:42"
    assert summary["von"] == {"name": "Tim Müller", "email": "tim@example.com"}
    assert summary["betreff"] == "Kino am Samstag?"
    assert summary["gelesen"] is True
    assert summary["datum"] == "2026-09-27T08:15:00+00:00"
    assert "Samstag mit ins Kino" in summary["vorschau"]


def test_html_mail_wird_zu_text():
    summary = imap._summary(ACC, "1", b"", make_mail(html=True))
    assert summary["vorschau"].startswith("Hey Levin,")
    assert "<b>" not in summary["vorschau"]
    assert summary["gelesen"] is False


def test_verschluesselung(monkeypatch):
    monkeypatch.setattr(get_settings(), "encryption_key", Fernet.generate_key().decode())
    token = crypto.encrypt("geheim123")
    assert "geheim123" not in token
    assert crypto.decrypt(token) == "geheim123"


def test_antwort_nur_mit_bestaetigung(monkeypatch):
    sent = []

    async def fake_read(db, mail_id):
        return {
            "konto": "levin@hispeed.ch",
            "betreff": "Kino am Samstag?",
            "antwort_an": "Tim Müller <tim@example.com>",
            "message_id": "<abc@example.com>",
            "references": "",
        }

    async def fake_send(db, payload):
        sent.append(payload)
        return {"gesendet": True}

    monkeypatch.setattr(service, "read", fake_read)
    monkeypatch.setattr(service, "send", fake_send)

    db = FakeDb()
    llm = FakeLlm(
        calls(("mail_senden", {"antwort_auf_id": "acc-1:42", "text": "Hey Tim, bin dabei! Levin"})),
        text("Antwort liegt zum Bestätigen bereit."),
    )
    pending = run(harness.chat(db, llm, "Antworte Tim, dass ich komme"))["pending"][0]

    assert pending["kind"] == "mail.send"
    assert pending["payload"]["betreff"] == "Re: Kino am Samstag?"
    assert pending["payload"]["an"] == "Tim Müller <tim@example.com>"
    assert pending["payload"]["in_reply_to"] == "<abc@example.com>"
    assert sent == []  # noch nichts gesendet

    run(actions.decide(db, pending["id"], True, {"text": "Hey Tim, klar, bin dabei!"}, TZ))
    assert sent[0]["text"] == "Hey Tim, klar, bin dabei!"
    assert sent[0]["konto_id"] == "acc-1"


def test_neue_mail_braucht_empfaenger():
    db = FakeDb()
    llm = FakeLlm(calls(("mail_senden", {"text": "Hallo"})), text("Wem denn?"))
    run(harness.chat(db, llm, "Schreib eine Mail"))
    assert db.tables["tool_log"][0]["ok"] is False
    assert "pending_actions" not in db.tables


def test_mail_id_zerlegen():
    assert service._split_id("0b1c-uuid:123") == ("0b1c-uuid", "123")
    with pytest.raises(imap.MailError):
        service._split_id("kaputt")


def test_mails_loeschen_nur_mit_bestaetigung(monkeypatch):
    trashed = []

    async def fake_trash(db, ids):
        trashed.extend(ids)
        return {"in_papierkorb": len(ids)}

    monkeypatch.setattr(service, "trash", fake_trash)
    service._cache[("acc-1", 30, 150, False)] = (
        "fp",
        [
            {
                "id": "acc-1:7",
                "von": {"name": "Zalando", "email": "news@zalando.ch"},
                "betreff": "-50%",
            }
        ],
    )
    db = FakeDb()
    llm = FakeLlm(
        calls(("mails_loeschen", {"ids": ["acc-1:7", "acc-1:7"], "grund": "Werbung"})),
        text("Hab 1 Werbemail zum Löschen hingelegt."),
    )
    pending = run(harness.chat(db, llm, "Lösch die Werbung"))["pending"][0]
    assert pending["kind"] == "mail.delete"
    assert pending["payload"]["anzahl"] == 1
    assert pending["payload"]["vorschau"][0]["von"] == "Zalando"
    assert trashed == []

    run(actions.decide(db, pending["id"], True, {}, TZ))
    assert trashed == ["acc-1:7"]
    service._cache.clear()


def test_newsletter_erkennung():
    msg = EmailMessage()
    msg["From"] = "Shop <news@shop.ch>"
    msg["Subject"] = "Sale"
    msg["List-Unsubscribe"] = "<mailto:unsub@shop.ch>"
    msg.set_content("Rabatt")
    assert imap._summary(ACC, "1", b"", msg.as_bytes())["newsletter"] is True
    assert imap._summary(ACC, "2", b"", make_mail())["newsletter"] is False


def test_papierkorb_ordner_finden():
    class FakeConn:
        def list(self):
            return "OK", [
                rb'(\HasNoChildren) "/" "INBOX"',
                rb'(\HasNoChildren \Trash) "/" "[Gmail]/Papierkorb"',
                rb'(\HasNoChildren) "." "Gesendet"',
            ]

    assert imap._special_folder(FakeConn(), r"\Trash") == '"[Gmail]/Papierkorb"'
    assert imap._special_folder(FakeConn(), r"\Sent") == '"Gesendet"'
