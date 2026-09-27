import asyncio

import httpx

from app import jev, router
from app.config import get_settings
from app.mail import classify


def run(coro):
    return asyncio.run(coro)


def mail(i, name, subject, newsletter=False):
    return {
        "id": f"a:{i}",
        "von": {"name": name, "email": f"{i}@x.ch"},
        "betreff": subject,
        "vorschau": "",
        "newsletter": newsletter,
    }


def fake_jev(monkeypatch, answers):
    sent = []

    async def fake_post(self, url, json=None, headers=None):
        sent.append(json)
        return httpx.Response(
            200, json={"answers": answers(json)}, request=httpx.Request("POST", url)
        )

    monkeypatch.setattr(get_settings(), "openrouter_api_key", "test")
    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    return sent


def test_mails_werden_eingeordnet_und_gemerkt(monkeypatch):
    classify._cache.clear()
    sent = fake_jev(
        monkeypatch,
        lambda body: {
            "k0": {"choice": "werbung"},
            "a0": {"noul": 0.1},
            "k1": {"choice": "persoenlich"},
            "a1": {"noul": 0.9},
        },
    )
    mails = [mail(1, "Zalando", "-50%"), mail(2, "Tim", "Kino?")]
    run(classify.annotate(mails))
    assert mails[0]["kategorie"] == "werbung" and not mails[0]["antwort_noetig"]
    assert mails[1]["kategorie"] == "persoenlich" and mails[1]["antwort_noetig"]
    assert len(sent) == 1 and len(sent[0]["questions"]) == 4

    run(classify.annotate([mail(1, "Zalando", "-50%")]))
    assert len(sent) == 1  # aus dem Zwischenspeicher, keine neue Anfrage
    classify._cache.clear()


def test_ohne_jev_einfache_regel():
    classify._cache.clear()
    mails = [mail(1, "Shop", "Sale", newsletter=True), mail(2, "Tim", "Hi")]
    run(classify.annotate(mails))
    assert [m["kategorie"] for m in mails] == ["werbung", None]
    classify._cache.clear()


def test_vorauswahl_der_tools(monkeypatch):
    fake_jev(
        monkeypatch,
        lambda body: {
            "kalender": {"noul": 0.9},
            "noten": {"noul": 0.8},
            "gym": {"noul": 0.05},
            "essen": {"noul": 0.1},
            "mails": {"noul": 0.02},
        },
    )
    groups = run(router.select_groups("Hab ne 5 in Mathe und Dienstag Zahnarzt", [], False))
    assert groups == {"kalender", "noten"}
    names = {d["name"] for d in router.declarations(groups)}
    assert {"note_eintragen", "termin_vorschlagen", "test_anlegen"} <= names
    assert "training_speichern" not in names and "mail_senden" not in names


def test_vorauswahl_foto_immer_essen(monkeypatch):
    fake_jev(monkeypatch, lambda body: {k: {"noul": 0.0} for k in body["questions"]})
    assert run(router.select_groups("was ist das?", [], True)) == {"essen"}


def test_vorauswahl_faellt_auf_alle_tools_zurueck(monkeypatch):
    async def broken(self, url, json=None, headers=None):
        raise httpx.ConnectError("weg")

    monkeypatch.setattr(get_settings(), "openrouter_api_key", "test")
    monkeypatch.setattr(httpx.AsyncClient, "post", broken)
    assert run(router.select_groups("hallo", [], False)) is None
    assert len(router.declarations(None)) == len(router.REGISTRY)
    assert jev.enabled()
