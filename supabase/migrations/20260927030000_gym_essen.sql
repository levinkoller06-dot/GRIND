-- GRIND · Phase 2: Training und Essen

create table public.workouts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  date date not null default current_date,
  title text,                         -- z. B. "Push", "Beine", "Laufen"
  notes text,
  created_at timestamptz not null default now()
);

create index workouts_user_date on public.workouts (user_id, date desc);

-- Eine Zeile pro Übung: "3×10 Liegestütze", "4×8 Bankdrücken 60 kg", "5 km Laufen in 30 min"
create table public.workout_entries (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  workout_id uuid not null references public.workouts (id) on delete cascade,
  exercise text not null,
  sets integer check (sets > 0),
  reps integer check (reps > 0),
  weight_kg numeric(6, 2) check (weight_kg >= 0),
  duration_min numeric(6, 1) check (duration_min > 0),
  distance_km numeric(6, 2) check (distance_km > 0),
  created_at timestamptz not null default now()
);

create index workout_entries_user_exercise on public.workout_entries (user_id, lower(exercise));

create table public.meals (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  eaten_at timestamptz not null default now(),
  meal_type text not null default 'snack'
    check (meal_type in ('fruehstueck', 'mittag', 'abend', 'snack')),
  description text,
  from_photo boolean not null default false,
  created_at timestamptz not null default now()
);

create index meals_user_eaten on public.meals (user_id, eaten_at desc);

create table public.meal_items (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  meal_id uuid not null references public.meals (id) on delete cascade,
  name text not null,
  amount text,                        -- z. B. "200 g", "1 Portion"
  kcal numeric(7, 1) not null default 0,
  protein_g numeric(6, 1) not null default 0,
  carbs_g numeric(6, 1) not null default 0,
  fat_g numeric(6, 1) not null default 0,
  created_at timestamptz not null default now()
);

create index meal_items_meal on public.meal_items (meal_id);

do $$
declare
  t text;
begin
  foreach t in array array['workouts', 'workout_entries', 'meals', 'meal_items'] loop
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
