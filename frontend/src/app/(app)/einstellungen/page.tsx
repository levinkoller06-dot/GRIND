import { SETTINGS_TAB } from "@/components/tabs";
import { createClient } from "@/lib/supabase/server";
import { signOut } from "@/app/login/actions";
import { SCALE_LABEL, type GradeScale } from "@/lib/grades";
import { saveProfile } from "./actions";

export default async function EinstellungenPage() {
  const supabase = await createClient();
  const { data } = await supabase.auth.getClaims();
  const { data: profile } = await supabase
    .from("profiles")
    .select("display_name, grade_scale")
    .eq("id", data?.claims?.sub ?? "")
    .maybeSingle();

  const field = "w-full rounded-xl border border-border bg-background px-3 py-2 text-sm";

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-black tracking-tight">
          {SETTINGS_TAB.icon} {SETTINGS_TAB.label}
        </h1>
        <p className="text-muted">{SETTINGS_TAB.description}</p>
      </header>

      <form action={saveProfile} className="space-y-4 rounded-2xl border border-border bg-surface p-4">
        <h2 className="font-bold">Profil</h2>
        <label className="block space-y-1">
          <span className="text-sm text-muted">Name</span>
          <input name="display_name" defaultValue={profile?.display_name ?? ""} className={field} />
        </label>
        <label className="block space-y-1">
          <span className="text-sm text-muted">Notenskala</span>
          <select name="grade_scale" defaultValue={profile?.grade_scale ?? "ch"} className={field}>
            {(Object.keys(SCALE_LABEL) as GradeScale[]).map((s) => (
              <option key={s} value={s}>
                {SCALE_LABEL[s]}
              </option>
            ))}
          </select>
        </label>
        <button className="rounded-xl bg-accent px-4 py-2 text-sm font-bold text-accent-fg">
          Speichern
        </button>
      </form>

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
