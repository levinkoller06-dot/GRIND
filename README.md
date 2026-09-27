# GRIND

Alltags-App für Schule, Gym und Leben – für mehrere Nutzer, mit einer KI im Zentrum, die alles selbst einsortiert.

**Status:** Phase 0 (Grundgerüst) · [Planung](docs/PLANUNG.md) · [Einrichtung](docs/SETUP.md)

## Konzept

- **Start-Tab = Gehirn:** Tagesübersicht + Chat. Einfach schreiben („Hab 3×10 Liegestütze gemacht und Donnerstag ist Mathetest“) – die KI trägt alles ein.
- **Tabs zum Durchklicken:** 📅 Kalender · 📊 Noten & Lernen · 💪 Gym & Essen · 📬 Mails & Pakete · 🎮 Freizeit · 💰 Geld
- **Bestätigung:** Termine und alles, was nach außen geht, schlägt die KI nur vor – eingetragen wird erst nach ✓.
- **Agent-Harness:** Die KI bekommt Tools (Termin eintragen, Training speichern, Note hinzufügen …) und entscheidet selbst, welche sie nutzt. Neue Funktion = neues Tool.

## Geplanter Stack

Python (FastAPI) · Gemini API · n8n (Zeitplan & Automationen) · Supabase (Login, Postgres, RLS) · Next.js (PWA) · Google APIs
