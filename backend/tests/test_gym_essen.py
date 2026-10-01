import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

from app import harness
from app.tools.base import ToolContext
from app.tools.essen import guess_meal_type, mahlzeit_eintragen
from app.tools.gym import training_speichern
from tests.fakes import FakeDb, FakeLlm, calls, text

TZ = ZoneInfo("Europe/Berlin")


def run(coro):
    return asyncio.run(coro)


def ctx(db):
    return ToolContext(db=db, tz=TZ, now=datetime(2026, 9, 27, 12, 30, tzinfo=TZ))


def test_training_und_rekord():
    db = FakeDb()
    first = run(
        training_speichern(
            ctx(db),
            {
                "uebungen": [
                    {"uebung": "Bankdrücken", "saetze": 4, "wiederholungen": 8, "gewicht_kg": 60},
                    {"uebung": "Liegestütze", "saetze": 3, "wiederholungen": 10},
                ]
            },
        )
    )
    assert first["uebungen"] == 2 and first["neue_rekorde"] == []

    second = run(
        training_speichern(
            ctx(db),
            {
                "uebungen": [
                    {"uebung": "bankdrücken", "saetze": 3, "wiederholungen": 5, "gewicht_kg": 65},
                    {"uebung": "Liegestütze", "saetze": 3, "wiederholungen": 12},
                ]
            },
        )
    )
    assert len(second["neue_rekorde"]) == 2
    assert "65" in second["neue_rekorde"][0]
    assert db.tables["workout_entries"][0]["sets"] == 4


def test_mahlzeit_summen():
    db = FakeDb()
    db.tables["profiles"] = [{"id": "user-1", "goal_kcal": 2500, "goal_protein_g": 150}]
    result = run(
        mahlzeit_eintragen(
            ctx(db),
            {
                "beschreibung": "Nudeln mit Hähnchen",
                "lebensmittel": [
                    {
                        "name": "Nudeln",
                        "menge": "250 g",
                        "kcal": 390,
                        "protein_g": 14,
                        "kh_g": 78,
                        "fett_g": 2,
                    },
                    {"name": "Hähnchen", "menge": "150 g", "kcal": 165, "protein_g": 35},
                ],
            },
        )
    )
    assert result["summe"] == {"kcal": 555.0, "protein_g": 49.0, "kh_g": 78.0, "fett_g": 2.0}
    assert db.tables["meals"][0]["meal_type"] == "mittag"
    assert db.tables["meals"][0]["eaten_at"].startswith("2026-09-27T12:30")
    assert result["tagesbilanz"]["ziel_protein_g"] == 150


def test_mahlzeit_typ():
    assert guess_meal_type(7) == "fruehstueck"
    assert guess_meal_type(19) == "abend"
    assert guess_meal_type(23) == "snack"


def test_foto_geht_an_ki_wird_aber_nicht_gespeichert():
    db = FakeDb()
    llm = FakeLlm(text("Sieht nach Pizza aus!"))
    run(harness.chat(db, llm, "Was ist das?", {"mime_type": "image/jpeg", "data": "QUJD"}))
    sent = llm.requests[0][-1]["parts"]
    assert sent[1] == {"inlineData": {"mimeType": "image/jpeg", "data": "QUJD"}}
    assert db.tables["chat_messages"][0]["content"] == "📷 Was ist das?"


def test_training_aus_chat():
    db = FakeDb()
    llm = FakeLlm(
        calls(
            (
                "training_speichern",
                {"uebungen": [{"uebung": "Liegestütze", "saetze": 3, "wiederholungen": 10}]},
            )
        ),
        text("Stark! 💪"),
    )
    assert run(harness.chat(db, llm, "3x10 Liegestütze"))["tools"] == ["training_speichern"]
    assert db.tables["workout_entries"][0]["reps"] == 10


def test_rezept_aus_json_ld():
    from app.tools.essen import parse_recipe

    html = """<html><head><script type="application/ld+json">
    {"@context": "https://schema.org", "@graph": [{"@type": "WebPage"},
     {"@type": ["Recipe"], "name": "Älplermagronen", "recipeYield": "4 Portionen",
      "recipeIngredient": ["400 g Hörnli", "200 g Kartoffeln"],
      "nutrition": {"@type": "NutritionInformation", "calories": "650 kcal"}}]}
    </script></head><body>…</body></html>"""
    recipe = parse_recipe(html)
    assert recipe["name"] == "Älplermagronen"
    assert recipe["zutaten"] == ["400 g Hörnli", "200 g Kartoffeln"]
    assert recipe["naehrwerte_laut_seite"] == {"calories": "650 kcal"}


def test_rezept_ohne_json_ld_liefert_text():
    from app.tools.essen import parse_recipe

    recipe = parse_recipe("<p>Zutaten: 2 Eier &amp; Speck</p><script>x()</script>")
    assert recipe == {"seitentext": "Zutaten: 2 Eier & Speck"}


def test_rezept_link_ins_eigene_netz_verboten():
    import pytest

    from app.net import public_url

    for url in ["http://localhost:8000/me", "http://192.168.1.1", "file:///etc/passwd"]:
        with pytest.raises(ValueError):
            public_url(url)
