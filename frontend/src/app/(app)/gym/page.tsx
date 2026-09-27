import { PageHeader } from "@/components/PageHeader";
import { TABS } from "@/components/tabs";
import { createClient } from "@/lib/supabase/server";
import { todayIso } from "@/lib/format";
import { daysFor, describeExercise, type PlanDay } from "@/lib/plan";

const tab = TABS.find((t) => t.href === "/gym")!;

export default async function GymPage() {
  const supabase = await createClient();
  const { data: claims } = await supabase.auth.getClaims();
  const today = todayIso();

  const [{ data: plan }, { count: doneToday }] = await Promise.all([
    supabase.from("training_plans").select("days").eq("user_id", claims?.claims?.sub ?? "").maybeSingle(),
    supabase.from("workouts").select("id", { count: "exact", head: true }).eq("date", today),
  ]);

  const days = (plan?.days ?? []) as PlanDay[];
  const todays = new Set(daysFor(days, today));

  return (
    <div className="flex flex-col md:min-h-0 md:flex-1">
      <PageHeader tab={tab}>
        {doneToday ? (
          <span className="rounded-xl bg-accent px-3 py-1.5 text-sm font-bold text-accent-fg">
            ✓ Heute trainiert
          </span>
        ) : (
          <span className="text-xs text-muted">Fertig? Sag „Training von heute gemacht“ 💪</span>
        )}
      </PageHeader>

      {days.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-border bg-surface p-8 text-center text-muted">
          Noch kein Trainingsplan. Schick dem Gehirn deinen Plan als Text, z. B.
          <br />
          „Hier ist mein Trainingsplan: Montag – Brust & Rücken, Brustpresse 3×8 …“
        </div>
      ) : (
        <div className="grid auto-rows-min gap-3 sm:grid-cols-2 lg:grid-cols-4 md:min-h-0 md:overflow-y-auto">
          {days.map((d) => {
            const isToday = todays.has(d);
            return (
              <section
                key={d.tag}
                className={`rounded-2xl border bg-surface p-3 ${
                  isToday ? "border-accent ring-2 ring-accent/30" : "border-border"
                } ${d.pause ? "opacity-75" : ""}`}
              >
                <div className="flex items-baseline justify-between gap-2">
                  <h2 className="truncate text-xs font-bold uppercase tracking-wide text-muted">{d.tag}</h2>
                  {isToday && (
                    <span className="rounded-full bg-accent px-2 text-[10px] font-bold text-accent-fg">
                      HEUTE
                    </span>
                  )}
                </div>
                <div className="font-bold">
                  {d.pause ? "😴 " : ""}
                  {d.titel}
                </div>
                {d.uebungen.length > 0 && (
                  <ul className="mt-1.5 space-y-0.5 text-sm">
                    {d.uebungen.map((e, i) => (
                      <li key={i} className="flex justify-between gap-2">
                        <span className="truncate">{e.uebung}</span>
                        <span className="shrink-0 text-xs text-muted">{describeExercise(e)}</span>
                      </li>
                    ))}
                  </ul>
                )}
                {d.hinweis && <p className="mt-1 text-xs text-muted">{d.hinweis}</p>}
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}
