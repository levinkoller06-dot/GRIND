-- GRIND · Phase 4: Mail-Konten (gemeinsames Postfach)
-- Mails selbst werden nicht gespeichert, sondern bei Bedarf live vom Server geholt.
-- Passwörter/Tokens liegen nur verschlüsselt hier (Schlüssel nur im Backend).

create table public.mail_accounts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  provider text not null default 'imap' check (provider in ('imap', 'microsoft')),
  email text not null,
  label text,                          -- z. B. "Privat", "Schule"
  color text,
  imap_host text,
  imap_port integer,
  smtp_host text,
  smtp_port integer,
  secret_enc text not null,            -- verschlüsseltes Passwort bzw. Refresh-Token
  created_at timestamptz not null default now()
);

create unique index mail_accounts_user_email on public.mail_accounts (user_id, lower(email));

alter table public.mail_accounts enable row level security;

create policy "Eigene Zeilen lesen" on public.mail_accounts
  for select to authenticated using ((select auth.uid()) = user_id);
create policy "Eigene Zeilen anlegen" on public.mail_accounts
  for insert to authenticated with check ((select auth.uid()) = user_id);
create policy "Eigene Zeilen ändern" on public.mail_accounts
  for update to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy "Eigene Zeilen löschen" on public.mail_accounts
  for delete to authenticated using ((select auth.uid()) = user_id);
