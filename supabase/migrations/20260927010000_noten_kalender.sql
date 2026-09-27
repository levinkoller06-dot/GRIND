-- GRIND · Phase 1: Noten, Tests und Kalender

create table public.subjects (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  name text not null,
  color text,
  created_at timestamptz not null default now()
);

create unique index subjects_user_name on public.subjects (user_id, lower(name));

create table public.grades (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  subject_id uuid not null references public.subjects (id) on delete cascade,
  value numeric(4, 2) not null,
  weight numeric(4, 2) not null default 1 check (weight > 0),
  kind text not null default 'test' check (kind in ('test', 'muendlich', 'sonstiges')),
  date date not null default current_date,
  note text,
  created_at timestamptz not null default now()
);

create index grades_user_subject on public.grades (user_id, subject_id);

create table public.exams (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  subject_id uuid not null references public.subjects (id) on delete cascade,
  date date not null,
  topics text,
  grade_id uuid references public.grades (id) on delete set null,
  created_at timestamptz not null default now()
);

create index exams_user_date on public.exams (user_id, date);

create table public.events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  title text not null,
  starts_at timestamptz not null,
  ends_at timestamptz,
  all_day boolean not null default false,
  kind text not null default 'termin' check (kind in ('schule', 'termin', 'test', 'geburtstag', 'sonstiges')),
  exam_id uuid references public.exams (id) on delete set null,
  notes text,
  google_event_id text,
  created_at timestamptz not null default now()
);

create index events_user_start on public.events (user_id, starts_at);

do $$
declare
  t text;
begin
  foreach t in array array['subjects', 'grades', 'exams', 'events'] loop
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
