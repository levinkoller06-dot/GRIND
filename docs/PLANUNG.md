# GRIND – Planung

Alltags-App für Schule, Gym und Leben, **für mehrere Nutzer**. Im Zentrum steht eine KI („das Gehirn“), die Anfragen versteht und selbst in die richtigen Bereiche einsortiert.

## 1. Grundidee

Statt viele einzelne Module zu programmieren, bekommt GRIND einen **KI-Kern (Agent-Harness)** mit Werkzeugen:

- **Die App** ist die Oberfläche: Start-Tab mit Chat plus Tabs zum Durchklicken.
- **Der Harness** ist das Herz: nimmt die Anfrage, gibt sie an die KI und führt die Tools aus, die die KI auswählt.
- **Tools** sind kleine Funktionen: „Termin vorschlagen“, „Training speichern“, „Note hinzufügen“, „Mails lesen“, „Mahlzeit eintragen“ …

Beispiel:
> „Hab heute 3×10 Liegestütze gemacht, Mittag gab's Nudeln mit Hähnchen und Donnerstag ist Mathetest.“

→ Training gespeichert, Mahlzeit mit Kalorien/Protein eingetragen, **Termin „Mathetest“ als Vorschlag zum Bestätigen**, Lernplan bis Donnerstag angelegt.

**Neue Funktion = ein neues Tool.** Tabs und KI nutzen **dieselbe Datenbank**: Was man im Tab von Hand einträgt, weiß die KI auch, und umgekehrt.

## 2. Aufbau der App

### Start-Tab: Das Gehirn
- Oben: Tagesübersicht, also heutiges Training, nächster Test, Kalorien/Protein, neue Mails, Pakete, **offene Vorschläge zum Bestätigen**
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
| ⚙️ **Einstellungen** | Profil, Google verbinden/trennen, Ziele |

## 3. Mehrere Nutzer

- **Anmeldung:** jeder Nutzer hat ein eigenes Konto (Supabase Auth: E-Mail oder „Mit Google anmelden“).
- **Getrennte Daten:** jede Tabelle hat eine `user_id`. Supabase **Row Level Security** sorgt dafür, dass jeder nur seine eigenen Daten sieht, auch wenn im Code mal ein Fehler ist.
- **Eigenes Google-Konto:** jeder Nutzer verbindet in den Einstellungen **sein eigenes** Gmail und seinen eigenen Google Kalender. Die Zugangs-Tokens werden verschlüsselt pro Nutzer gespeichert.
- **Harness pro Nutzer:** jede Chat-Anfrage läuft mit der `user_id` des Absenders. Die Tools können nur auf dessen Daten zugreifen.
- **Limits:** tägliches KI-Limit pro Nutzer, damit einer nicht das ganze kostenlose Kontingent aufbraucht.
- **Später möglich:** Teilen zwischen Freunden (z. B. gemeinsame Gym-Rekorde, Lerngruppen).

## 4. Bestätigung von Terminen und Aktionen

Die KI trägt **keinen Termin selbst ein**. Sie macht einen **Vorschlag**:

```
KI:  Soll ich das eintragen?
     ┌──────────────────────────────────┐
     │ 📅 Mathetest                      │
     │ Do, 02.10. · ganztägig            │
     │ Kalender: Schule                  │
     │ [✓ Eintragen] [✎ Ändern] [✕ Nein] │
     └──────────────────────────────────┘
```

- Erst nach **✓ Eintragen** wird der Termin gespeichert und in den Google Kalender geschrieben.
- Offene Vorschläge erscheinen auch in der Tagesübersicht.
- Technisch: Tools für Termine legen einen Eintrag in `pending_actions` an (Status: `offen` → `bestätigt` / `abgelehnt`). Erst das Bestätigen führt die Aktion aus.

**Was braucht Bestätigung?**
| Mit Bestätigung | Direkt (aber rückgängig machbar) |
|---|---|
| Termine anlegen, ändern, löschen | Training speichern |
| Mails senden | Mahlzeit eintragen |
| Antwort-Entwürfe in Gmail anlegen | Note eintragen |
| Alles, was nach außen geht | Watchlist, Ausgaben, Sparziele |

## 5. Architektur

```
┌──────────────── App (Handy / PC) ────────────────┐
│  Login · Start-Tab (Übersicht + Chat) · Tabs     │
└───────────────┬──────────────────────────────────┘
                │ mit Login-Token (user_id)
                ▼
┌──────────── Python-Backend (Gehirn) ─────────────┐
│  Harness: Nachricht → KI → Tool-Aufrufe → Antwort│
│  Tools (pro Nutzer): kalender, noten, training,  │
│    essen, mails, geld …                          │
│  Bestätigungen: pending_actions                  │
│  Google-Anbindung pro Nutzer (Kalender + Gmail)  │
└──────┬─────────────────────────────┬─────────────┘
       ▼                             ▲ Webhooks
  Supabase (Postgres,          ┌──── n8n ─────────────────┐
  Auth, Fotos)                 │ Zeitplan-Jobs: Morgen-   │
                               │ Check, Mail-Abruf, Pakete│
                               │ Preise, Free Games       │
                               └──────────────────────────┘
```

### Aufgaben von Python und n8n

Weil jeder Nutzer sein eigenes Google-Konto verbindet, läuft **Google (Gmail + Kalender) im Python-Backend**: Das Backend verwaltet die Tokens pro Nutzer. n8n kann Zugangsdaten nur fest pro Workflow speichern, nicht pro Nutzer.

- **n8n macht die Zeitpläne und allgemeine Sachen:** stößt regelmäßig Jobs im Backend an (z. B. „neue Mails für alle Nutzer abrufen und zusammenfassen“, „Morgen-Check senden“). Allgemeine Daten wie Free Games und Gaming-News holt n8n selbst, weil sie für alle gleich sind. Paketstatus und Preis-Wächter kommen ebenfalls über n8n.
- **Python macht:** Login-Prüfung, Chat, Harness, alle Tools, Google-Anbindung pro Nutzer und die Datenbank.
- **Verbindung:** n8n ruft geschützte Backend-Endpunkte auf (`/jobs/...`) und schickt Ergebnisse per Webhook. Beide Seiten prüfen einen gemeinsamen geheimen Schlüssel.
- **n8n betreiben:** lokal per Docker oder später auf einem kleinen Server.

### Regeln für den Harness
1. **Bestätigung vor Terminen und allem nach außen** (siehe Abschnitt 4).
2. **Nicht alles braucht KI:** Erinnerungen, Timer, Morgen-Check, Paket- und Preisabfragen laufen als normaler Code nach Zeitplan.
3. **Jede Aktion wird geloggt**, damit man sieht, was die KI gemacht hat.
4. **Nur eigene Daten:** Tools bekommen immer die `user_id` und können nichts anderes sehen.
5. **KI-Anbieter austauschbar:** Start mit Gemini, später wechselbar zu z. B. Claude.

## 6. Technik

| Bereich | Wahl | Warum |
|---|---|---|
| Harness / Backend | **Python + FastAPI** | Volle Kontrolle, man lernt am meisten |
| KI | **Gemini API** (Function Calling, Bilder für Essensfotos) | Günstig, kostenloses Kontingent zum Start |
| Datenbank + Login | **Supabase** (Postgres, Auth, Row Level Security, Speicher für Fotos) | Mehrere Nutzer von Anfang an sicher getrennt |
| App | **Next.js als PWA** (TypeScript, Tailwind) | Am Handy installierbar, läuft auch am PC |
| Zeitplan / Automationen | **n8n** (Docker) | Jobs anstoßen, allgemeine Daten holen |
| Kalender + Mail | Google Calendar API + Gmail API (im Backend, OAuth pro Nutzer) | Jeder verbindet sein eigenes Konto |
| Nährwerte | Open Food Facts | Kostenlos, Barcodes |

Supabase gibt es kostenlos (Cloud) oder lokal per Docker. Zum Entwickeln reicht die kostenlose Cloud-Version.

## 7. Tools (erste Liste)

| Bereich | Tools |
|---|---|
| Kalender | `termin_vorschlagen`*, `termine_abfragen`, `termin_aendern`*, `termin_loeschen`* |
| Noten & Lernen | `note_eintragen`, `test_anlegen` (Termin dazu mit *), `lernplan_erstellen`, `karteikarten_erzeugen`, `schnitt_berechnen` |
| Gym | `training_speichern`, `trainings_abfragen`, `rekord_pruefen` |
| Essen | `mahlzeit_eintragen` (Text/Foto), `naehrwerte_suchen`, `tagesbilanz` |
| Mails | `mails_zusammenfassen`, `antwort_entwerfen`*, `mail_senden`* |
| Pakete | `paket_hinzufuegen`, `paketstatus` |
| Freizeit | `free_games`, `watchlist_hinzufuegen` |
| Geld | `ausgabe_eintragen`, `sparziel_setzen`, `preis_beobachten` |

\* erzeugt einen Vorschlag, wird erst nach Bestätigung ausgeführt

## 8. Datenmodell (erste Version)

Alle Tabellen haben `user_id` und Row Level Security.

- `profiles`: Name, Ziele (Kalorien, Protein), Einstellungen, KI-Limit
- `google_connections`: verschlüsselte Tokens, verbundene Konten
- `pending_actions`: Typ, Daten (JSON), Status, erstellt von (Chat/Tab)
- `events`: Titel, Start, Ende, Typ (Schule/Termin/Test/Geburtstag), Google-ID
- `subjects`, `grades`: Fach, Note, Gewichtung, Datum
- `exams`: Fach, Datum, Themen · `flashcards`: Frage, Antwort, nächste Wiederholung
- `workouts`, `workout_sets`: Übung, Sätze, Wiederholungen, Gewicht
- `meals`, `meal_items`: Name, Menge, kcal, Protein, KH, Fett, Foto
- `mail_summaries`: Gmail-ID, Kategorie, Zusammenfassung, Entwurf
- `packages`: Sendungsnummer, Anbieter, Status
- `transactions`, `savings_goals`, `price_watches`
- `watchlist`
- `chat_messages`, `tool_log`: Verlauf und was die KI ausgeführt hat

## 9. Fahrplan

| Phase | Inhalt | Ergebnis |
|---|---|---|
| **0 – Setup** | Python-Backend, Supabase (Login + Tabellen + RLS), Next.js-App mit Login und Tab-Gerüst | Man kann sich anmelden, leere Tabs |
| **1 – Gehirn** | Harness mit Gemini, Chat im Start-Tab, Tools für Noten + Kalender (lokal) mit **Bestätigungs-Karten** | „Donnerstag Mathetest“ → Vorschlag → bestätigen |
| **2 – Gym & Essen** | Training + Mahlzeiten (Text und Foto), Tab mit Fortschritt | Täglicher Nutzen |
| **3 – Google** | „Mit Google verbinden“ pro Nutzer, bestätigte Termine landen im Google Kalender, Google-Termine werden angezeigt | Echter Kalender |
| **4 – Mails** | Gmail pro Nutzer: Zusammenfassung, Sortierung, Antwort-Entwürfe (mit Bestätigung) | Mail-Helfer |
| **5 – Zeitplan & n8n** | n8n aufsetzen: Morgen-Check, Mail-Abruf, Erinnerungen | App meldet sich selbst |
| **6 – Lernen & Extras** | Lernplan, Karteikarten, Pakete, Geld, Freizeit | Alle Tabs |
| **7 – Online & Sprache** | Hosting, Handy-Installation, Spracheingabe | Freunde können mitmachen |

## 10. Wichtig bei mehreren Nutzern

- **Google-Freigabe:** Solange die App im Google-„Testmodus“ ist, können bis zu 100 Nutzer mitmachen, die man vorher als Tester einträgt. Die Anmeldung läuft dann nach 7 Tagen ab und muss erneuert werden. Für Gmail-Zugriff ohne diese Grenzen verlangt Google eine aufwendige Prüfung. Für einen Freundeskreis reicht der Testmodus.
- **Gemini kostenlos:** Im kostenlosen Kontingent darf Google die Eingaben zur Verbesserung nutzen, und es gibt Anfrage-Limits. Bei Mails von mehreren Leuten lohnt sich später die bezahlte Stufe (dann keine Nutzung zum Training, sehr günstig pro Anfrage).
- **Datenschutz:** Mails und Noten von Freunden sind sensible Daten. Nutzer müssen zustimmen und ihr Konto samt Daten löschen können.

## 11. Datenschutz & Sicherheit

- API-Schlüssel nur in `.env`, nie im Repo
- Google-Tokens verschlüsselt in der Datenbank
- Row Level Security auf allen Tabellen
- KI verschickt oder trägt nichts nach außen ein ohne Bestätigung
- „Konto löschen“ entfernt alle Daten des Nutzers
