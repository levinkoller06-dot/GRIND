# GRIND

Alltags-App für Schule, Gym und Leben – mit einer KI im Zentrum, die alles selbst einsortiert.

**Status:** Planung – siehe [docs/PLANUNG.md](docs/PLANUNG.md)

## Konzept

- **Start-Tab = Gehirn:** Tagesübersicht + Chat. Einfach schreiben („Hab 3×10 Liegestütze gemacht und Donnerstag ist Mathetest“) – die KI trägt alles ein.
- **Tabs zum Durchklicken:** 📅 Kalender · 📊 Noten & Lernen · 💪 Gym & Essen · 📬 Mails & Pakete · 🎮 Freizeit · 💰 Geld
- **Agent-Harness:** Die KI bekommt Tools (Termin eintragen, Training speichern, Note hinzufügen …) und entscheidet selbst, welche sie nutzt. Neue Funktion = neues Tool.

## Geplanter Stack

Python (FastAPI) · Gemini API · n8n (Mails & Automationen) · SQLite → Supabase · Next.js (PWA) · Google APIs
