import { SETTINGS_TAB } from "@/components/tabs";
import { createClient } from "@/lib/supabase/server";
import { signOut } from "@/app/login/actions";
import { SCALE_LABEL, type GradeScale } from "@/lib/grades";
import { MailAccounts } from "@/components/MailAccounts";
import { MoodleConnect } from "@/components/MoodleConnect";
import { MorningCheck } from "@/components/MorningCheck";
import { saveProfile } from "./actions";

export default async function EinstellungenPage() {
  const supabase = await createClient();
  const { data } = await supabase.auth.getClaims();
  const { data: profile } = await supabase
    .from("profiles")
    .select("display_name, grade_scale, goal_kcal, goal_protein_g")
    .eq("id", data?.claims?.sub ?? "")
    .maybeSingle();
  // Getrennt abfragen: fehlt die Zeitplan-Migration, soll der Rest trotzdem laden
  const { data: schedule, error: scheduleError } = await supabase
    .from("profiles")
    .select("morning_check_time")
    .eq("id", data?.claims?.sub ?? "")
    .maybeSingle();

  const field = "w-full rounded-xl border border-border bg-background px-3 py-2 text-sm";

  return (
    <div className="space-y-4 md:overflow-y-auto">
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
        <div className="grid grid-cols-2 gap-3">
          <label className="block space-y-1">
            <span className="text-sm text-muted">Ziel Kalorien / Tag</span>
            <input name="goal_kcal" type="number" min={0} defaultValue={profile?.goal_kcal ?? ""} className={field} />
          </label>
          <label className="block space-y-1">
            <span className="text-sm text-muted">Ziel Protein (g) / Tag</span>
            <input name="goal_protein_g" type="number" min={0} defaultValue={profile?.goal_protein_g ?? ""} className={field} />
          </label>
        </div>
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

      <MorningCheck time={scheduleError ? undefined : (schedule?.morning_check_time ?? null)} />
      <MailAccounts />
      <MoodleConnect />
    </div>
  );
}
