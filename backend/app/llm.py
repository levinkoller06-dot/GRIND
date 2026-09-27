import asyncio
import json
from typing import Any

import httpx

API = "https://generativelanguage.googleapis.com/v1beta/models"


class LlmError(Exception):
    pass


class Gemini:
    """Minimaler Gemini-Client (REST) mit Function Calling und JSON-Antworten."""

    def __init__(self, api_key: str, model: str, fallback_model: str | None = None):
        self.api_key = api_key
        self.models = [m for m in (model, fallback_model) if m]

    async def _post(self, body: dict) -> dict[str, Any]:
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
