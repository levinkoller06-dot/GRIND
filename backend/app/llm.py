import asyncio
from typing import Any

import httpx

API = "https://generativelanguage.googleapis.com/v1beta/models"


class LlmError(Exception):
    pass


class Gemini:
    """Minimaler Gemini-Client (REST) mit Function Calling."""

    def __init__(self, api_key: str, model: str, fallback_model: str | None = None):
        self.api_key = api_key
        self.models = [m for m in (model, fallback_model) if m]

    async def generate(
        self,
        system: str,
        contents: list[dict],
        tools: list[dict],
    ) -> dict[str, Any]:
        """Gibt den `content` der Modell-Antwort zurück (role + parts)."""
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": contents,
            "tools": [{"functionDeclarations": tools}] if tools else [],
        }
        last_error = ""
        async with httpx.AsyncClient(timeout=60) as http:
            for model in self.models:
                for attempt in range(2):
                    res = await http.post(
                        f"{API}/{model}:generateContent",
                        json=body,
                        headers={"x-goog-api-key": self.api_key},
                    )
                    if res.is_success:
                        candidates = res.json().get("candidates") or []
                        if not candidates or "content" not in candidates[0]:
                            raise LlmError("Leere Antwort vom Modell")
                        return candidates[0]["content"]
                    last_error = f"{model}: {res.status_code} {res.text[:300]}"
                    # Überlastet / Limit: kurz warten, dann nochmal bzw. nächstes Modell
                    if res.status_code in (429, 500, 503) and attempt == 0:
                        await asyncio.sleep(1.5)
                        continue
                    break
        raise LlmError(last_error)
