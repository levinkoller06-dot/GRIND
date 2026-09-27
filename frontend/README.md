# GRIND Frontend

Next.js 16 (App Router) + Tailwind + Supabase Auth. Einrichtung: [../docs/SETUP.md](../docs/SETUP.md)

| Pfad | Inhalt |
|---|---|
| `src/app/(app)/` | Start-Tab und alle Tabs (nur angemeldet) |
| `src/app/login/` | Anmelden / Registrieren |
| `src/app/auth/callback/` | Ziel des Bestätigungslinks |
| `src/proxy.ts` | Session erneuern, nicht Angemeldete zu `/login` schicken |
| `src/lib/supabase/` | Supabase-Clients (Browser, Server, Proxy) |
| `src/components/` | Tab-Navigation, Platzhalter |
