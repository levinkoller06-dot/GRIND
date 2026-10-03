-- GRIND · Phase 5: Zeitplan (Morgen-Check, Erinnerungen, Mail-Abruf)
-- Die Jobs laufen im Backend mit dem Secret Key. Meldungen landen in `notifications`
-- und erscheinen als Karte im Gehirn-Tab (später zusätzlich als Push).

-- Uhrzeit für den Morgen-Check (null = aus) und letzter Mail-Abruf
alter table public.profiles
  add column morning_check_time time default '06:30',
  add column mail_checked_at timestamptz;

-- Erinnerungen, die der Nutzer per Chat setzt ("erinner mich morgen um 7 an die Sporttasche")
create table public.reminders (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  text text not null,
  due_at timestamptz not null,
  done_at timestamptz,
  created_at timestamptz not null default now()
);

create index reminders_open on public.reminders (due_at) where done_at is null;

-- Meldungen an den Nutzer. `key` verhindert Doppelte (z. B. "morgen:2026-10-03").
create table public.notifications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  kind text not null check (kind in ('morgen', 'erinnerung', 'mail')),
  title text not null,
  body text,
  link text,
  key text,
  read_at timestamptz,
  created_at timestamptz not null default now()
);

create unique index notifications_user_key on public.notifications (user_id, key);
create index notifications_user_unread on public.notifications (user_id, created_at desc)
  where read_at is null;

do $$
declare
  t text;
begin
  foreach t in array array['reminders', 'notifications'] loop
    execute format('alter table public.%I enable row level security', t);
    execute format(
      'create policy "Eigene Zeilen lesen" on public.%I for select to authenticated using ((select auth.uid()) = user_id)', t);
    execute format(
      'create policy "Eigene Zeilen anlegen" on public.%I for insert to authenticated with check ((select auth.uid()) = user_id)', t);
    execute format(
      'create policy "Eigene Zeilen ändern" on public.%I for update to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id)', t);
    execute format(
      'create policy "Eigene Zeilen löschen" on public.%I for delete to authenticated using ((select auth.uid()) = user_id)', t);
  end loop;
end;
$$;
