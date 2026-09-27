# GRIND Backend

Python + FastAPI. Prüft das Supabase-Login-Token und spricht im Namen des Nutzers mit der Datenbank (Row Level Security greift).

```bash
uv sync
uv run uvicorn app.main:app --reload --port 8000
uv run pytest
```

| Datei | Inhalt |
|---|---|
| `app/main.py` | API-Endpunkte (`/health`, `/me`) |
| `app/auth.py` | Token-Prüfung (JWKS oder HS256) |
| `app/db.py` | Supabase-REST-Client pro Nutzer |
| `app/config.py` | Einstellungen aus `.env` |
