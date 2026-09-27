"""Jev (TypeSafe AI) über die Decisions API von OpenRouter.

Jev ist kein Chat-Modell: Es beantwortet nur typisierte Fragen über einen Zustand
(`choice` = eine Option wählen, `noul` = Wahrscheinlichkeit für Ja, `score`).
Dafür ist es sehr schnell (~0,4 s) und sehr günstig. In GRIND nutzen wir es für
Entscheidungen, bei denen die Antwortmöglichkeiten feststehen – freie Texte,
Tool-Aufrufe und Bilder bleiben bei Gemini.
"""

from typing import Any

import httpx

from app.config import get_settings

URL = "https://openrouter.ai/api/alpha/decisions"


class JevError(Exception):
    pass


def enabled() -> bool:
    return bool(get_settings().openrouter_api_key)


def choice(instructions: str, options: dict[str, str]) -> dict:
    return {"type": "choice", "instructions": instructions, "criteria": options}


def noul(instructions: str) -> dict:
    return {
        "type": "noul",
        "instructions": instructions,
        "criteria": {"true": "ja", "false": "nein"},
    }


async def decide(state: str, questions: dict[str, dict], timeout: float = 8) -> dict[str, Any]:
    """Stellt mehrere Fragen in einer Anfrage und gibt die Antworten nach Namen zurück."""
    settings = get_settings()
    if not settings.openrouter_api_key:
        raise JevError("OPENROUTER_API_KEY fehlt in backend/.env")
    try:
        async with httpx.AsyncClient(timeout=timeout) as http:
            res = await http.post(
                URL,
                headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
                json={"model": settings.jev_model, "state": state, "questions": questions},
            )
    except httpx.HTTPError as e:
        raise JevError(f"Jev nicht erreichbar: {e}") from e
    data = res.json() if res.content else {}
    if not res.is_success:
        raise JevError(f"Jev ({res.status_code}): {data.get('error', {}).get('message', '')[:200]}")
    return data.get("answers") or {}
