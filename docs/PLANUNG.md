# GRIND – Planung

Persönliche Alltags-App für Schule, Gym und Leben. Im Zentrum steht eine KI („das Gehirn“), die Anfragen versteht und selbst in die richtigen Bereiche einsortiert.

## 1. Grundidee

Statt viele einzelne Module zu programmieren, bekommt GRIND einen **KI-Kern (Agent-Harness)** mit Werkzeugen:

- **Die App** ist die Oberfläche: Start-Tab mit Chat plus Tabs zum Durchklicken.
- **Der Harness** ist das Herz: nimmt die Anfrage, gibt sie an die KI und führt die Tools aus, die die KI auswählt.
- **Tools** sind kleine Funktionen: „Termin eintragen“, „Training speichern“, „Note hinzufügen“, „Mails lesen“, „Mahlzeit eintragen“ …

Beispiel:
> „Hab heute 3×10 Liegestütze gemacht, Mittag gab's Nudeln mit Hähnchen und Donnerstag ist Mathetest.“

→ Training gespeichert, Mahlzeit mit Kalorien/Protein eingetragen, Test im Kalender, Lernplan bis Donnerstag angelegt, alles in einem Schritt.

**Neue Funktion = ein neues Tool.** Tabs und KI nutzen **dieselbe Datenbank**: Was ich im Tab von Hand eintrage, weiß die KI auch, und umgekehrt.

## 2. Aufbau der App

### Start-Tab: Das Gehirn
- Oben: Tagesübersicht, also heutiges Training, nächster Test, Kalorien/Protein, neue Mails, Pakete
- Darunter: Chat (Text, später Sprache). Die KI sortiert alles selbst in die Tabs.

### Tabs zum Durchklicken
| Tab | Inhalt |
|---|---|
| 📅 **Kalender** | Schule, Termine, Tests, Geburtstage |
| 📊 **Noten & Lernen** | Fächer, Noten, Schnitt, Tests, Lernplan, Karteikarten |
| 💪 **Gym & Essen** | Trainingsplan, Fortschritt, Rekorde, Mahlzeiten, Kalorien, Protein |
| 📬 **Mails & Pakete** | Mail-Zusammenfassungen, Antwort-Entwürfe, Lieferstatus |
| 🎮 **Freizeit** | Gaming-News, Free Games, Watchlist |
| 💰 **Geld** | Taschengeld, Sparziele, Preis-Wächter |

## 3. Architektur

```
┌──────────────── App (Handy / PC) ────────────────┐
│  Start-Tab (Übersicht + Chat)   │  Tabs          │
└───────────────┬─────────────────┴───────┬────────┘
                │ Chat-Nachricht          │ normale Abfragen
                ▼                         ▼
┌──────────── Backend ─────────────────────────────┐
│  Harness: Nachricht → KI → Tool-Aufrufe → Antwort│
│  Tools: kalender, noten, training, essen, mails… │
│  Zeitplan-Jobs (ohne KI): Erinnerungen, Morgen-  │
│  Check, Paket-/Preis-Abfragen                    │
└───────────────┬──────────────────────────────────┘
                ▼
        Datenbank  ·  Google Kalender/Gmail  ·  externe APIs
```

### Regeln für den Harness
1. **Nachfragen vor Änderungen nach außen:** Mails senden, Termine löschen und Ähnliches passieren erst nach Bestätigung per Button. Einfaches Speichern (Training, Mahlzeit, Note) läuft direkt, lässt sich aber rückgängig machen.
2. **Nicht alles braucht KI:** Erinnerungen, Timer, Morgen-Check, Paket- und Preisabfragen laufen als normaler Code nach Zeitplan. Das ist schneller, gratis und zuverlässiger.
3. **Jede Aktion wird geloggt**, damit man sieht, was die KI gemacht hat.
4. **KI-Anbieter austauschbar:** Start mit Gemini (kostenloses Kontingent), später wechselbar zu z. B. Claude.

## 4. Technik (Vorschlag)

| Bereich | Wahl | Warum |
|---|---|---|
| Harness / Backend | **Python + FastAPI** | Volle Kontrolle, man lernt am meisten |
| KI | **Gemini API** (Function Calling, Bilder für Essensfotos) | Kostenloses Kontingent reicht für den Alltag |
| Datenbank | **SQLite** am Anfang → später **Supabase (Postgres)** | Einfach starten, später online |
| App | **Next.js als PWA** (TypeScript, Tailwind) | Am Handy installierbar, läuft auch am PC |
| Zeitplan-Jobs | APScheduler (im Backend) | Erinnerungen, Morgen-Check |
| Kalender / Mail | Google Calendar API, Gmail API | Direkte Anbindung |
| Nährwerte | Open Food Facts | Kostenlos, Barcodes |

Alternative zum Python-Harness: **n8n** mit dem „AI Agent“-Baustein. Tools werden dort per Drag-and-Drop verbunden, das ist schneller für den Einstieg, gibt aber weniger Kontrolle. Empfehlung: Python.

## 5. Tools (erste Liste)

| Bereich | Tools |
|---|---|
| Kalender | `termin_eintragen`, `termine_abfragen`, `termin_loeschen`* |
| Noten & Lernen | `note_eintragen`, `test_anlegen`, `lernplan_erstellen`, `karteikarten_erzeugen`, `schnitt_berechnen` |
| Gym | `training_speichern`, `trainings_abfragen`, `rekord_pruefen` |
| Essen | `mahlzeit_eintragen` (Text/Foto), `naehrwerte_suchen`, `tagesbilanz` |
| Mails | `mails_zusammenfassen`, `antwort_entwerfen`, `mail_senden`* |
| Pakete | `paket_hinzufuegen`, `paketstatus` |
| Freizeit | `free_games`, `watchlist_hinzufuegen` |
| Geld | `ausgabe_eintragen`, `sparziel_setzen`, `preis_beobachten` |

\* nur mit Bestätigung

## 6. Datenmodell (erste Version)

- `events`: Titel, Start, Ende, Typ (Schule/Termin/Test/Geburtstag), Google-ID
- `subjects`, `grades`: Fach, Note, Gewichtung, Datum
- `exams`: Fach, Datum, Themen · `flashcards`: Frage, Antwort, nächste Wiederholung
- `workouts`, `workout_sets`: Übung, Sätze, Wiederholungen, Gewicht
- `meals`, `meal_items`: Name, Menge, kcal, Protein, KH, Fett, Foto
- `packages`: Sendungsnummer, Anbieter, Status
- `transactions`, `savings_goals`, `price_watches`
- `watchlist`
- `chat_messages`, `tool_log`: Verlauf und was die KI ausgeführt hat

## 7. Fahrplan

| Phase | Inhalt | Ergebnis |
|---|---|---|
| **0 – Setup** | Python-Backend, Datenbank, Next.js-App mit Tab-Gerüst | Leere App läuft |
| **1 – Gehirn** | Harness mit Gemini, Chat im Start-Tab, erste Tools: Kalender (lokal) + Noten | „Donnerstag Mathetest“ funktioniert |
| **2 – Gym & Essen** | Training + Mahlzeiten (Text und Foto), Tab mit Fortschritt | Täglicher Nutzen |
| **3 – Übersicht & Zeitplan** | Tagesübersicht, Morgen-Check, Erinnerungen | App meldet sich selbst |
| **4 – Lernen** | Lernplan bis zum Test, Karteikarten | Lernmodul |
| **5 – Google** | Google Kalender + Gmail (Zusammenfassung, Entwürfe) | Echte Daten |
| **6 – Extras** | Pakete, Geld, Freizeit | Alle Tabs |
| **7 – Online & Sprache** | Hosting, Handy-Installation, Spracheingabe | Überall nutzbar |

## 8. Offene Fragen

1. Python oder n8n für den Harness? (Empfehlung: Python)
2. Soll die App nur für mich sein oder auch für Freunde?
3. Welche Mail-Adresse und welcher Kalender sollen angebunden werden? (Plan geht von Google aus)

## 9. Datenschutz

- API-Schlüssel nur in `.env`, nie im Repo
- Daten in der eigenen Datenbank
- KI verschickt nie selbstständig etwas, immer erst nach Bestätigung
