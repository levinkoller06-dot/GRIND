import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from app import harness
from app.tools.base import ToolContext
from app.tools.gym import trainingsplan_abfragen, trainingsplan_setzen, trainingsplan_tag_aendern
from app.tools.noten import fach_loeschen, faecher_anlegen, match_subject, note_eintragen
from tests.fakes import FakeDb

TZ = ZoneInfo("Europe/Berlin")


def run(coro):
    return asyncio.run(coro)


def ctx(db):
    return ToolContext(db=db, tz=TZ, now=datetime(2026, 9, 28, 12, tzinfo=TZ))  # Montag


def test_faecher_und_aliase():
    db = FakeDb()
    result = run(
        faecher_anlegen(
            ctx(db),
            {
                "faecher": [
                    {"name": "ABU", "aliase": ["Gesellschaft", "Sprache und Kommunikation"]},
                    {"name": "Modul 114"},
                    {"name": "abu"},
                ]
            },
        )
    )
    assert result == {"angelegt": ["ABU", "Modul 114"], "gab_es_schon": ["abu"]}

    run(note_eintragen(ctx(db), {"fach": "sprache und  kommunikation", "note": 5}))
    assert len(db.tables["subjects"]) == 2
    assert db.tables["grades"][0]["subject_id"] == db.tables["subjects"][0]["id"]


def test_fach_mit_noten_nicht_loeschen():
    db = FakeDb()
    run(note_eintragen(ctx(db), {"fach": "Mathe", "note": 4}))
    with pytest.raises(ValueError, match="1 Note"):
        run(fach_loeschen(ctx(db), {"fach": "mathe"}))


def test_match_subject():
    subjects = [{"name": "Englisch", "aliases": ["English", "E"]}]
    assert match_subject(subjects, "english")["name"] == "Englisch"
    assert match_subject(subjects, "Mathe") is None


def test_trainingsplan():
    db = FakeDb()
    run(
        trainingsplan_setzen(
            ctx(db),
            {
                "tage": [
                    {
                        "tag": "Montag",
                        "titel": "Brust & Rücken",
                        "uebungen": [
                            {
                                "uebung": "Brustpresse",
                                "saetze": 3,
                                "wiederholungen": 8,
                                "stufe": "11",
                            }
                        ],
                    },
                    {"tag": "Mittwoch", "titel": "Pause", "pause": True, "uebungen": []},
                ]
            },
        )
    )
    run(
        trainingsplan_tag_aendern(
            ctx(db), {"tag": {"tag": "montag", "titel": "Brust", "uebungen": []}}
        )
    )
    plan = run(trainingsplan_abfragen(ctx(db), {}))
    assert plan["heute"] == "Montag"
    assert [d["titel"] for d in plan["tage"]] == ["Brust", "Pause"]
    assert len(db.tables["training_plans"]) == 1


def test_faecher_im_prompt():
    now = datetime(2026, 9, 28, 12, tzinfo=TZ)
    prompt = harness.system_prompt(now, None, "ch", [{"name": "ABU", "aliases": ["Gesellschaft"]}])
    assert "ABU (auch: Gesellschaft)" in prompt
