-- GRIND · Phase 0: Grundlage
-- Jede Tabelle gehört einem Nutzer (user_id) und ist per Row Level Security
-- geschützt: Jeder sieht und ändert nur seine eigenen Zeilen.

-- ---------------------------------------------------------------------------
-- Profile
-- ---------------------------------------------------------------------------
create table public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  display_name text,
  timezone text not null default 'Europe/Berlin',
  goal_kcal integer,
  goal_protein_g integer,
  ai_daily_limit integer not null default 100,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.profiles enable row level security;

create policy "Profil lesen" on public.profiles
  for select to authenticated using ((select auth.uid()) = id);
create policy "Profil ändern" on public.profiles
  for update to authenticated using ((select auth.uid()) = id) with check ((select auth.uid()) = id);

-- Profil automatisch bei der Registrierung anlegen
create function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.profiles (id, display_name)
  values (new.id, new.raw_user_meta_data ->> 'display_name');
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- updated_at automatisch setzen
create function public.set_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger profiles_updated_at
  before update on public.profiles
  for each row execute function public.set_updated_at();

-- ---------------------------------------------------------------------------
-- Chat-Verlauf mit dem Gehirn
-- ---------------------------------------------------------------------------
create table public.chat_messages (
  id bigint generated always as identity primary key,
  user_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  role text not null check (role in ('user', 'assistant', 'tool')),
  content text not null,
  created_at timestamptz not null default now()
);

create index chat_messages_user_created on public.chat_messages (user_id, created_at desc);

-- ---------------------------------------------------------------------------
-- Vorschläge, die der Nutzer erst bestätigen muss (z. B. Termine)
-- ---------------------------------------------------------------------------
create table public.pending_actions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  kind text not null,                -- z. B. 'event.create', 'mail.send'
  payload jsonb not null,            -- Daten des Vorschlags
  status text not null default 'open' check (status in ('open', 'confirmed', 'rejected', 'failed')),
  source text not null default 'chat' check (source in ('chat', 'tab', 'job')),
  created_at timestamptz not null default now(),
  decided_at timestamptz
);

create index pending_actions_open on public.pending_actions (user_id) where status = 'open';

-- ---------------------------------------------------------------------------
-- Protokoll: was hat die KI ausgeführt?
-- ---------------------------------------------------------------------------
create table public.tool_log (
  id bigint generated always as identity primary key,
  user_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  tool text not null,
  arguments jsonb not null default '{}',
  result jsonb,
  ok boolean not null default true,
  created_at timestamptz not null default now()
);

create index tool_log_user_created on public.tool_log (user_id, created_at desc);

-- ---------------------------------------------------------------------------
-- Gleiche RLS-Regeln für alle Nutzer-Tabellen
-- ---------------------------------------------------------------------------
do $$
declare
  t text;
begin
  foreach t in array array['chat_messages', 'pending_actions', 'tool_log'] loop
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
