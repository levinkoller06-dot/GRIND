-- GRIND · Fach-Aliase und Trainingsplan

-- Weitere Namen für ein Fach, z. B. ABU = "Gesellschaft", "Sprache und Kommunikation"
alter table public.subjects
  add column aliases text[] not null default '{}';

-- Ein Wochen-Trainingsplan pro Nutzer
-- days: [{ "tag": "Montag", "titel": "Brust & Rücken", "pause": false,
--          "uebungen": [{ "uebung": "Brustpresse", "saetze": 3, "wiederholungen": 8, "stufe": "11" }],
--          "hinweis": null }]
create table public.training_plans (
  user_id uuid primary key default auth.uid() references auth.users (id) on delete cascade,
  days jsonb not null default '[]',
  updated_at timestamptz not null default now()
);

alter table public.training_plans enable row level security;

create policy "Eigene Zeilen lesen" on public.training_plans
  for select to authenticated using ((select auth.uid()) = user_id);
create policy "Eigene Zeilen anlegen" on public.training_plans
  for insert to authenticated with check ((select auth.uid()) = user_id);
create policy "Eigene Zeilen ändern" on public.training_plans
  for update to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy "Eigene Zeilen löschen" on public.training_plans
  for delete to authenticated using ((select auth.uid()) = user_id);
