"""Mails mit Jev einordnen: Kategorie + ob eine Antwort nötig ist."""

import asyncio
import logging

from app import jev

log = logging.getLogger(__name__)

CATEGORIES = {
    "werbung": "Werbung, Newsletter, Angebote, Shops, Gewinnspiele, Social-Media-Hinweise",
    "persoenlich": "Persönliche Nachricht von einem Menschen (Freunde, Familie)",
    "schule": "Schule, Ausbildung, Lehrbetrieb, Arbeit",
    "rechnung": "Rechnung, Bestellung, Lieferung, Zahlung, Abo",
    "sicherheit": "Sicherheit, Konto, Anmeldung, Passwort, Bestätigungscode",
    "sonstiges": "Alles andere (Info-Mails, Benachrichtigungen)",
}

BATCH = 40

# Mail-ID → {"kategorie": ..., "antwort_noetig": bool}; Mails ändern sich nicht, also reicht ein Mal
_cache: dict[str, dict] = {}

# Ab dieser Wahrscheinlichkeit gilt eine Mail als sichere Werbung (wird automatisch weggeräumt)
SURE_AD = 0.8
# Mail-IDs, die Jev selbst sicher als Werbung erkannt hat (nicht nur die Ersatzregel)
_sure_ads: set[str] = set()


def sure_ads(mails: list[dict]) -> list[str]:
    return [m["id"] for m in mails if m["id"] in _sure_ads]


def _line(i: int, m: dict) -> str:
    flag = " (hat Abmelde-Link)" if m.get("newsletter") else ""
    preview = (m.get("vorschau") or "")[:160]
    return f"[{i}] Von: {m['von']['name']} <{m['von']['email']}>{flag}\nBetreff: {m['betreff']}\n{preview}"


def _fallback(m: dict) -> dict:
    return {"kategorie": "werbung" if m.get("newsletter") else None, "antwort_noetig": False}


async def _classify_batch(mails: list[dict]) -> None:
    state = "Mails im Posteingang eines Schülers:\n\n" + "\n\n".join(
        _line(i, m) for i, m in enumerate(mails)
    )
    questions = {}
    for i in range(len(mails)):
        questions[f"k{i}"] = jev.choice(f"Kategorie von Mail [{i}]", CATEGORIES)
        questions[f"a{i}"] = jev.noul(
            f"Erwartet der Absender von Mail [{i}] eine persönliche Antwort vom Empfänger?"
        )
    answers = await jev.decide(state, questions)
    for i, m in enumerate(mails):
        category = answers.get(f"k{i}", {}).get("choice")
        reply = answers.get(f"a{i}", {}).get("noul", 0)
        ad_prob = answers.get(f"k{i}", {}).get("probabilities", {}).get("werbung", 0)
        if category == "werbung" and ad_prob >= SURE_AD:
            _sure_ads.add(m["id"])
        _cache[m["id"]] = {
            "kategorie": category if category in CATEGORIES else _fallback(m)["kategorie"],
            "antwort_noetig": category in ("persoenlich", "schule") and reply >= 0.6,
        }


async def annotate(mails: list[dict]) -> list[dict]:
    """Ergänzt jede Mail um `kategorie` und `antwort_noetig` (ohne Jev: einfache Regel)."""
    todo = [m for m in mails if m["id"] not in _cache]
    if todo and jev.enabled():
        # Alle Pakete gleichzeitig an Jev schicken statt nacheinander
        batches = [todo[start : start + BATCH] for start in range(0, len(todo), BATCH)]
        results = await asyncio.gather(
            *(_classify_batch(b) for b in batches), return_exceptions=True
        )
        for e in results:
            if isinstance(e, jev.JevError):
                log.warning("Mail-Einordnung mit Jev fehlgeschlagen: %s", e)
            elif isinstance(e, Exception):
                raise e
    for m in mails:
        m.update(_cache.get(m["id"]) or _fallback(m))
    return mails
