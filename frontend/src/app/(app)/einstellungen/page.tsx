import { SETTINGS_TAB } from "@/components/tabs";
import { createClient } from "@/lib/supabase/server";
import { signOut } from "@/app/login/actions";

export default async function EinstellungenPage() {
  const supabase = await createClient();
  const { data } = await supabase.auth.getClaims();

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-black tracking-tight">
          {SETTINGS_TAB.icon} {SETTINGS_TAB.label}
        </h1>
        <p className="text-muted">{SETTINGS_TAB.description}</p>
      </header>

      <section className="rounded-2xl border border-border bg-surface p-4">
        <h2 className="font-bold">Konto</h2>
        <p className="text-sm text-muted">{data?.claims?.email}</p>
        <form action={signOut} className="mt-4">
          <button className="rounded-xl border border-border px-4 py-2 text-sm font-medium hover:bg-surface-2">
            Abmelden
          </button>
        </form>
      </section>

      <section className="rounded-2xl border border-dashed border-border bg-surface p-4 text-sm text-muted">
        Google verbinden (Kalender + Gmail) kommt in Phase 3.
      </section>
    </div>
  );
}
