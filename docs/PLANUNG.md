# GRIND – Planung

Persönliche Alltags-App: ein Ort für Essen, Lernen, Termine und Mails, mit KI-Unterstützung.

## 1. Ziel

Eine App, die ich jeden Tag öffne und die mir zeigt:
- was heute ansteht (Termine, Tests, Aufgaben),
- wie ich heute gegessen habe,
- was ich lernen sollte,
- welche Mails eine Antwort brauchen.

Und die mir Arbeit abnimmt: Essen per Foto erfassen, Lernfragen erzeugen, Termine eintragen, Mail-Antworten vorschlagen.

## 2. Module

### 2.1 Dashboard „Heute“
- Tagesübersicht: Termine, fällige Aufgaben, nächste Tests, Kalorien/Makros, offene Mails
- Kurzer KI-Tagesbrief am Morgen („Heute: Mathe-Test in 3 Tagen, 2 Mails warten“)

### 2.2 Essen-Tracking
- Mahlzeit per **Foto** (KI schätzt Gericht, Kalorien, Eiweiß/Kohlenhydrate/Fett), per **Text** („2 Brote mit Käse“) oder **Barcode** (Open Food Facts)
- Tagesziele (Kalorien, Protein), Wasser
- Verlauf und Wochenstatistik
- Favoriten / häufige Mahlzeiten mit einem Tipp erneut eintragen

### 2.3 Lernen & Tests
- Fächer und Tests mit Datum anlegen → landet automatisch im Kalender
- Lernplan: App verteilt Lerneinheiten bis zum Testdatum
- Karteikarten mit Spaced Repetition (Wiederholung nach Vergessenskurve)
- KI erzeugt Karteikarten / Quizfragen aus Notizen, Fotos vom Heft oder PDFs
- Nach dem Test: Note eintragen, Notenschnitt pro Fach

### 2.4 Kalender & Aufgaben
- Anbindung an **Google Kalender** (lesen + schreiben)
- Termine per Sprache/Text eintragen („Nächsten Dienstag 15 Uhr Zahnarzt“) → KI macht daraus einen Termin
- Einfache To-do-Liste mit Fälligkeiten

### 2.5 Mails
- Anbindung an **Gmail** (Lesen, Entwürfe erstellen)
- KI sortiert: „braucht Antwort“, „nur Info“, „Werbung“
- KI schreibt Antwort-**Entwürfe**; gesendet wird erst nach meiner Bestätigung
- Kurze Zusammenfassung langer Mails

### 2.6 Später: Assistent
- Chat/Sprache als zentrale Eingabe („Trag ein, dass ich Pizza gegessen hab“)
- Mögliche Verbindung zum Sprachassistenten aus dem Projekt NEXO

## 3. Technik (Vorschlag)

| Bereich | Wahl | Warum |
|---|---|---|
| App | **Next.js (React, TypeScript) als PWA** | Läuft am Handy (installierbar) und am PC, ein Code |
| UI | Tailwind CSS + shadcn/ui | Schnell, sieht gut aus |
| Datenbank + Login | **Supabase** (Postgres, Auth, Speicher für Fotos) | Kostenloser Einstieg, kein eigener Server nötig |
| KI | **Claude API** (Vision für Essensfotos, Text für Mails/Lernen/Termine) | Ein Anbieter für alles |
| Kalender / Mail | Google Calendar API, Gmail API (OAuth) | Direkte Anbindung |
| Nährwerte | Open Food Facts API | Kostenlos, Barcodes |
| Hosting | Vercel | Gratis für Privatprojekte, Deploy bei jedem Push |

Alternative, falls die App sich eher „nativ“ anfühlen soll: Expo (React Native). Empfehlung: erst PWA, wechseln ist später möglich.

## 4. Datenmodell (erste Version)

- `profiles` – Ziele (Kalorien, Protein), Einstellungen
- `meals` – Datum, Typ (Frühstück…), Foto, Einträge
- `meal_items` – Name, Menge, kcal, Protein, KH, Fett
- `subjects` – Fach, Farbe
- `exams` – Fach, Datum, Themen, Note
- `flashcards` – Fach, Frage, Antwort, nächste Wiederholung, Intervall
- `study_sessions` – geplante/erledigte Lerneinheiten
- `tasks` – Titel, fällig am, erledigt
- `mail_triage` – Gmail-ID, Kategorie, Zusammenfassung, Entwurf

## 5. Fahrplan

| Phase | Inhalt | Ergebnis |
|---|---|---|
| **0 – Setup** | Next.js-Projekt, Supabase, Login, Deploy auf Vercel, PWA | Leere App läuft am Handy |
| **1 – Heute + Aufgaben** | Dashboard, To-dos | Erster täglicher Nutzen |
| **2 – Essen** | Manuell + Foto-Erkennung mit Claude, Tagesziele, Statistik | Essen-Tracking komplett |
| **3 – Lernen** | Fächer, Tests, Karteikarten, Spaced Repetition, KI-Karten aus Notizen | Lernmodul |
| **4 – Kalender** | Google Kalender verbinden, Tests automatisch eintragen, Termine per Text | Alles an einem Ort |
| **5 – Mails** | Gmail verbinden, Sortierung, Zusammenfassung, Antwort-Entwürfe | Mail-Helfer |
| **6 – Assistent** | Chat/Sprache als zentrale Eingabe, Morgenbrief | „Alles per Satz“ |

Jede Phase ist für sich nutzbar – nach Phase 2 hat man schon eine brauchbare App.

## 6. Offene Fragen

1. Hauptsächlich am Handy, am PC oder beides?
2. Schule, Ausbildung oder Uni? (beeinflusst Noten-System und Lernplan)
3. Welcher Mail-/Kalenderanbieter? (Plan geht von Google aus)
4. Nur für mich oder sollen andere die App auch nutzen können?
5. Budget für die KI-API (Foto-Erkennung kostet pro Bild ein paar Zehntel Cent)?

## 7. Datenschutz

- API-Schlüssel nur in `.env.local`, nie im Repo
- Mails und Essensfotos nur im eigenen Supabase-Projekt
- KI sendet nie selbstständig Mails – immer nur Entwürfe
