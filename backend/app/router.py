"""Vorauswahl der Tools mit Jev: Welche Bereiche betrifft eine Nachricht?

Gemini bekommt danach nur die Tools dieser Bereiche statt aller – das spart Tokens
(günstiger, etwas schneller) und verringert Verwechslungen. Klappt Jev nicht oder ist
nichts eindeutig, bekommt Gemini wie bisher alle Tools.
"""

import logging

from app import jev
from app.tools import REGISTRY

log = logging.getLogger(__name__)

GROUPS = {
    "kalender": "Termine, Kalender, Verabredungen, Geburtstage (eintragen, abfragen, löschen)",
    "noten": "Schule: Noten, Fächer, Tests und Prüfungen",
    "gym": "Sport: Training, Übungen, Trainingsplan, Rekorde",
    "essen": "Essen: Mahlzeiten, Kalorien, Protein, Ernährungsziele",
    "mails": "E-Mails: lesen, suchen, zusammenfassen, beantworten, schreiben, löschen",
}

# Tools, die zu mehreren Bereichen gehören
EXTRA = {"eintrag_loeschen": {"essen", "gym"}, "test_anlegen": {"noten", "kalender"}}

THRESHOLD = 0.3


def tool_groups(name: str) -> set[str]:
    module = REGISTRY[name].handler.__module__.rsplit(".", 1)[-1]
    return EXTRA.get(name, set()) | {module}


async def select_groups(message: str, recent: list[str], has_image: bool) -> set[str] | None:
    """Gibt die betroffenen Bereiche zurück oder None (= alle Tools verwenden)."""
    if not jev.enabled():
        return None
    context = "\n".join(recent[-3:])
    state = (
        f"Bisheriger Chat (Auszug):\n{context or '(leer)'}\n\n"
        f"Neue Nachricht des Nutzers an seine Alltags-App:\n{message}"
        + ("\n(Mit einem Foto im Anhang.)" if has_image else "")
    )
    questions = {
        key: jev.noul(f"Braucht die App für die neue Nachricht diesen Bereich: {desc}?")
        for key, desc in GROUPS.items()
    }
    try:
        answers = await jev.decide(state, questions, timeout=4)
    except jev.JevError as e:
        log.warning("Tool-Vorauswahl mit Jev fehlgeschlagen: %s", e)
        return None
    groups = {k for k in GROUPS if answers.get(k, {}).get("noul", 1) >= THRESHOLD}
    if has_image:
        groups.add("essen")
    return groups or None


def declarations(groups: set[str] | None) -> list[dict]:
    return [
        t.declaration()
        for name, t in REGISTRY.items()
        if groups is None or tool_groups(name) & groups
    ]
