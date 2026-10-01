import pytest

from app.config import get_settings


@pytest.fixture(autouse=True)
def keine_echten_apis(monkeypatch):
    """Tests sollen nie echte KI-/Jev-Anfragen stellen, auch wenn Keys in .env stehen."""
    monkeypatch.setattr(get_settings(), "openrouter_api_key", "")
    # Die meisten Tests prüfen den Ablauf mit Bestätigung; ohne gibt es eigene Tests
    monkeypatch.setattr(get_settings(), "confirm_actions", True)
