-- GRIND · Notenskala pro Nutzer, Ort und Personen bei Terminen

-- 'ch': 6 = beste Note, 4 = genügend, 1 = schlechteste (Schweiz)
-- 'de': 1 = beste Note, 4 = ausreichend, 6 = schlechteste (Deutschland)
alter table public.profiles
  add column grade_scale text not null default 'ch' check (grade_scale in ('ch', 'de'));

alter table public.events
  add column location text,
  add column participants text[] not null default '{}';
