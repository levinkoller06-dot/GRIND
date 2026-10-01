"""Moodle-Kalender (iCal-Export) in den GRIND-Kalender übernehmen.

Moodle liefert Abgaben („… ist fällig.“), Prüfungen („… beginnt“) und Kurstermine.
Abgaben landen als ganztägiger Schul-Termin am Abgabetag, Prüfungen und Tests als Test.
"""

import re
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from app import net
from app.db import Db
from app.mail.crypto import decrypt, encrypt

PREFIX = "moodle:"
# Bei jedem Öffnen der App höchstens so oft neu abrufen
MIN_INTERVAL = timedelta(minutes=15)


class MoodleError(Exception):
    pass


def _unescape(value: str) -> str:
    return re.sub(r"\\([\\,;nN])", lambda m: "\n" if m[1] in "nN" else m[1], value)


def parse_ics(text: str) -> list[dict]:
    """Minimaler iCal-Parser: gibt jede VEVENT als {FELD: Wert} zurück."""
    lines = re.sub(r"\r?\n[ \t]", "", text).splitlines()  # umbrochene Zeilen zusammenfügen
    events, current = [], None
    for line in lines:
        if line == "BEGIN:VEVENT":
            current = {}
        elif line == "END:VEVENT" and current is not None:
            events.append(current)
            current = None
        elif current is not None and ":" in line:
            key, value = line.split(":", 1)
            current[key.split(";")[0]] = _unescape(value)
    return events


def _when(value: str) -> datetime:
    if value.endswith("Z"):
        return datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
    return datetime.strptime(value[:8], "%Y%m%d").replace(tzinfo=UTC)


def to_event(raw: dict, tz: ZoneInfo) -> dict | None:
    if not raw.get("UID") or not raw.get("DTSTART"):
        return None
    title = raw.get("SUMMARY", "").strip()
    course = raw.get("CATEGORIES", "").split(",")[0].strip()
    start = _when(raw["DTSTART"])
    event = {
        "external_id": PREFIX + raw["UID"],
        "notes": " · ".join(filter(None, ["Moodle", course, raw.get("DESCRIPTION", "").strip()]))[
            :1000
        ],
    }
    if title.endswith(" ist fällig."):
        # Abgabe: ganztägig am (lokalen) Abgabetag, Abgabe meist um 23:59
        day = start.astimezone(tz).date()
        midnight = datetime.combine(day, datetime.min.time(), tz)
        return event | {
            "title": f"📚 {title.removesuffix(' ist fällig.')}",
            "starts_at": midnight.isoformat(),
            "ends_at": None,
            "all_day": True,
            "kind": "schule",
        }
    is_test = bool(re.search(r"prüfung|test|klausur|quiz", title, re.IGNORECASE))
    return event | {
        "title": title.removesuffix(" beginnt").removesuffix(" endet"),
        "starts_at": start.isoformat(),
        "ends_at": None,
        "all_day": False,
        "kind": "test" if is_test else "schule",
    }


async def _profile(db: Db) -> dict:
    rows = await db.select(
        "profiles", select="timezone,moodle_ical_enc,moodle_synced_at", id=f"eq.{db.user.id}"
    )
    return rows[0] if rows else {}


async def _download(url: str) -> list[dict]:
    try:
        res = await net.fetch(url, timeout=15)
    except ValueError as e:
        raise MoodleError(str(e)) from e
    except Exception as e:
        raise MoodleError(f"Moodle nicht erreichbar: {e}") from e
    if "BEGIN:VCALENDAR" not in res.text[:500]:
        raise MoodleError("Das ist kein Kalender-Link (Moodle → Kalender → Exportieren)")
    return parse_ics(res.text)


async def sync(db: Db, force: bool = False) -> dict:
    """Gleicht die Moodle-Termine ab: neue anlegen, geänderte anpassen, entfernte löschen."""
    profile = await _profile(db)
    if not profile.get("moodle_ical_enc"):
        return {"verbunden": False}
    last = profile.get("moodle_synced_at")
    now = datetime.now(UTC)
    if not force and last and now - datetime.fromisoformat(last) < MIN_INTERVAL:
        return {"verbunden": True, "uebersprungen": True, "zuletzt": last}

    tz = ZoneInfo(profile.get("timezone") or "Europe/Berlin")
    raw = await _download(decrypt(profile["moodle_ical_enc"]))
    wanted = {e["external_id"]: e for e in filter(None, (to_event(r, tz) for r in raw))}

    existing = await db.select(
        "events",
        select="id,external_id,title,starts_at,all_day,kind,notes",
        external_id=f"like.{PREFIX}*",
    )
    have = {e["external_id"]: e for e in existing}
    new = [{"user_id": db.user.id, **e} for k, e in wanted.items() if k not in have]
    await db.insert_many("events", new)

    changed = 0
    for key, event in wanted.items():
        old = have.get(key)
        fields = ("title", "all_day", "kind", "notes")
        if old and (
            any(old[f] != event[f] for f in fields)
            or datetime.fromisoformat(old["starts_at"])
            != datetime.fromisoformat(event["starts_at"])
        ):
            await db.update("events", event, id=f"eq.{old['id']}")
            changed += 1

    # In Moodle gelöscht: nur künftige Termine entfernen (ältere fallen aus dem Export heraus)
    removed = 0
    for key, old in have.items():
        if key not in wanted and datetime.fromisoformat(old["starts_at"]) > now:
            await db.delete("events", id=f"eq.{old['id']}")
            removed += 1

    await db.update("profiles", {"moodle_synced_at": now.isoformat()}, id=f"eq.{db.user.id}")
    return {
        "verbunden": True,
        "neu": len(new),
        "geaendert": changed,
        "entfernt": removed,
        "zuletzt": now.isoformat(),
    }


async def connect(db: Db, url: str) -> dict:
    """Prüft den Link, speichert ihn verschlüsselt und holt sofort die Termine."""
    await _download(url)
    await db.update(
        "profiles",
        {"moodle_ical_enc": encrypt(url.strip()), "moodle_synced_at": None},
        id=f"eq.{db.user.id}",
    )
    return await sync(db, force=True)


async def disconnect(db: Db) -> None:
    await db.update(
        "profiles", {"moodle_ical_enc": None, "moodle_synced_at": None}, id=f"eq.{db.user.id}"
    )
    await db.delete("events", external_id=f"like.{PREFIX}*")


async def status(db: Db) -> dict:
    profile = await _profile(db)
    return {
        "verbunden": bool(profile.get("moodle_ical_enc")),
        "zuletzt": profile.get("moodle_synced_at"),
    }
