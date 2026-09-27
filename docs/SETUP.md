# GRIND – Einrichtung

## Was du brauchst

- [Node.js](https://nodejs.org) (ab 20)
- [uv](https://docs.astral.sh/uv/) (installiert Python automatisch)
- Ein kostenloses Konto auf [supabase.com](https://supabase.com)

## 1. Supabase-Projekt anlegen

1. Auf supabase.com ein neues Projekt erstellen (Region: Frankfurt / `eu-central-1`).
2. **SQL Editor** öffnen und den Inhalt von
   [`supabase/migrations/20260927000000_grundlage.sql`](../supabase/migrations/20260927000000_grundlage.sql)
   einfügen und ausführen.
3. **Project Settings → API**: die **Project URL** und den **Publishable Key** (`sb_publishable_...`) kopieren.
4. **Authentication → URL Configuration**:
   - Site URL: `http://localhost:3000`
   - Redirect URLs: `http://localhost:3000/auth/callback`

> Zum schnellen Testen kannst du unter **Authentication → Sign In / Providers → Email** „Confirm email“ ausschalten. Dann bist du nach der Registrierung sofort angemeldet.

## 2. Backend (Python)

```bash
cd backend
cp .env.example .env      # SUPABASE_URL und SUPABASE_PUBLISHABLE_KEY eintragen
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

Test: http://localhost:8000/health → `{"status":"ok"}` · API-Doku: http://localhost:8000/docs

Tests: `uv run pytest`

## 3. Frontend (App)

```bash
cd frontend
cp .env.local.example .env.local   # URL und Publishable Key eintragen
npm install
npm run dev
```

App: http://localhost:3000 → registrieren → Start-Tab. Unten steht „Backend: verbunden“, wenn alles klappt.

## Am Handy testen

Handy und PC im selben WLAN: `npm run dev -- -H 0.0.0.0` und am Handy `http://<IP-deines-PCs>:3000` öffnen.
Die App lässt sich über „Zum Startbildschirm hinzufügen“ installieren, richtig als PWA aber erst mit HTTPS (Phase 7).

## Projektstruktur

```
backend/     Python + FastAPI – das Gehirn (Harness, Tools, Google)
frontend/    Next.js-App – Start-Tab, Tabs, Login
supabase/    Datenbank-Schema (SQL-Migrationen)
docs/        Planung und Einrichtung
```
