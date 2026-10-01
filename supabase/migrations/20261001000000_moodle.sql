-- Moodle-Kalender (z. B. BZU): Abgaben und Prüfungen automatisch in den Kalender

-- Export-Link (verschlüsselt, enthält ein Zugangs-Token) und letzter Abgleich
alter table public.profiles
  add column moodle_ical_enc text,
  add column moodle_synced_at timestamptz;

-- Herkunft importierter Termine (z. B. "moodle:100526@moodle.bzu.ch"), damit nichts doppelt kommt
alter table public.events
  add column external_id text;

create unique index events_user_external on public.events (user_id, external_id)
  where external_id is not null;
