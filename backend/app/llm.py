import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import httpx

API = "https://generativelanguage.googleapis.com/v1beta/models"
TIMEOUT = httpx.Timeout(45, connect=10)

# Modelle, deren Tageskontingent aufgebraucht ist: Modell → Zeitpunkt, ab dem es wieder geht.
# Google setzt das Kontingent um Mitternacht (Pazifik-Zeit) zurück.
_exhausted: dict[str, float] = {}


class LlmError(Exception):
    pass


def _next_quota_reset() -> float:
    now = datetime.now(ZoneInfo("America/Los_Angeles"))
    midnight = datetime.combine(now.date() + timedelta(days=1), datetime.min.time(), now.tzinfo)
    return midnight.timestamp()


class Gemini:
    """Minimaler Gemini-Client (REST) mit Function Calling und JSON-Antworten.

    Probiert die Modelle der Reihe nach: Ist eines überlastet, zu langsam oder sein
    Tageskontingent aufgebraucht, wird automatisch das nächste genommen.
    """

    def __init__(self, api_key: str, models: list[str]):
        self.api_key = api_key
        self.models = [m for m in models if m]

    async def _post(self, body: dict) -> dict[str, Any]:
        errors: list[str] = []
        quota_only = True
        available = [m for m in self.models if _exhausted.get(m, 0) < time.time()]
        async with httpx.AsyncClient(timeout=TIMEOUT) as http:
            for model in available:
                for attempt in range(2):
                    try:
                        res = await http.post(
                            f"{API}/{model}:generateContent",
                            json=body,
                            headers={"x-goog-api-key": self.api_key},
                        )
                    except httpx.TimeoutException:
                        errors.append(f"{model}: Zeitüberschreitung")
                        quota_only = False
                        break  # zu langsam → nächstes Modell
                    except httpx.TransportError as e:
                        errors.append(f"{model}: {e}")
                        quota_only = False
                        break

                    if res.is_success:
                        candidates = res.json().get("candidates") or []
                        if not candidates or "content" not in candidates[0]:
                            raise LlmError("Leere Antwort vom Modell")
                        return candidates[0]["content"]

                    errors.append(f"{model}: {res.status_code}")
                    if res.status_code == 429 and "PerDay" in res.text:
                        _exhausted[model] = _next_quota_reset()
                        break  # für heute aufgebraucht → nächstes Modell
                    quota_only = quota_only and res.status_code == 429
                    if res.status_code in (429, 500, 503) and attempt == 0:
                        await asyncio.sleep(1.5)
                        continue
                    break

        if not available or (quota_only and errors):
            raise LlmError(
                "Das kostenlose KI-Kontingent ist für heute aufgebraucht. "
                "Es wird um 9 Uhr morgens (Schweizer Zeit) zurückgesetzt."
            )
        raise LlmError("; ".join(errors))

    async def generate(
        self,
        system: str,
        contents: list[dict],
        tools: list[dict],
    ) -> dict[str, Any]:
        """Gibt den `content` der Modell-Antwort zurück (role + parts)."""
        return await self._post(
            {
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": contents,
                "tools": [{"functionDeclarations": tools}] if tools else [],
            }
        )

    async def generate_json(self, system: str, prompt: str, schema: dict) -> Any:
        """Antwort als JSON-Objekt nach vorgegebenem Schema."""
        content = await self._post(
            {
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "responseJsonSchema": schema,
                },
            }
        )
        text = "".join(p.get("text", "") for p in content.get("parts", []) if not p.get("thought"))
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise LlmError(f"Ungültiges JSON vom Modell: {text[:200]}") from e
