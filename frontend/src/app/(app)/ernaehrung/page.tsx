import { MealSuggestions } from "@/components/MealSuggestions";
import { PageHeader } from "@/components/PageHeader";
import { TABS } from "@/components/tabs";
import { createClient } from "@/lib/supabase/server";
import { dayEnd, dayStart, todayIso } from "@/lib/format";
import { round, sum, type Meal } from "@/lib/nutrition";
import { addDays, dayKey, weekdayShort } from "@/lib/week";

const tab = TABS.find((t) => t.href === "/ernaehrung")!;

function Progress({ label, value, goal, unit }: { label: string; value: number; goal: number | null; unit: string }) {
  const pct = goal ? Math.min(100, (value / goal) * 100) : 0;
  return (
    <div>
      <div className="flex justify-between text-sm">
        <span className="text-muted">{label}</span>
        <span>
          <b>{round(value)}</b>
          {goal ? ` / ${round(goal)}` : ""} {unit}
        </span>
      </div>
      <div className="mt-1 h-2.5 overflow-hidden rounded-full bg-surface-2">
        <div className="h-full rounded-full bg-accent" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default async function ErnaehrungPage() {
  const supabase = await createClient();
  const { data: claims } = await supabase.auth.getClaims();
  const today = todayIso();
  const weekStart = addDays(today, -6);

  const [{ data: profile }, { data: mealData }] = await Promise.all([
    supabase
      .from("profiles")
      .select("goal_kcal, goal_protein_g")
      .eq("id", claims?.claims?.sub ?? "")
      .maybeSingle(),
    supabase
      .from("meals")
      .select("id,eaten_at,meal_type,description,from_photo,meal_items(name,amount,kcal,protein_g,carbs_g,fat_g)")
      .gte("eaten_at", dayStart(weekStart))
      .lte("eaten_at", dayEnd(today)),
  ]);

  const meals = (mealData ?? []) as Meal[];
  const todaySum = sum(meals.filter((m) => dayKey(m.eaten_at) === today).flatMap((m) => m.meal_items));
  const goalKcal = profile?.goal_kcal ?? null;
  const goalProtein = profile?.goal_protein_g ?? null;

  const week = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i)).map((d) => {
    const s = sum(meals.filter((m) => dayKey(m.eaten_at) === d).flatMap((m) => m.meal_items));
    return { day: d, kcal: s.kcal, protein: s.protein_g };
  });
  const maxProtein = Math.max(goalProtein ?? 0, ...week.map((w) => w.protein), 1);

  const card = "rounded-2xl border border-border bg-surface p-4";

  return (
    <div className="flex flex-col md:min-h-0 md:flex-1">
      <PageHeader tab={tab} />

      <div className="grid gap-4 md:min-h-0 md:flex-1 lg:grid-cols-2">
        <div className="flex flex-col gap-4">
          <section className={`${card} space-y-3`}>
            <h2 className="font-bold">🍗 Heute gegessen</h2>
            <Progress label="Kalorien" value={todaySum.kcal} goal={goalKcal} unit="kcal" />
            <Progress label="Protein" value={todaySum.protein_g} goal={goalProtein} unit="g" />
            <div className="flex gap-4 text-xs text-muted">
              <span>Kohlenhydrate {round(todaySum.carbs_g)} g</span>
              <span>Fett {round(todaySum.fat_g)} g</span>
            </div>
            {!goalKcal && !goalProtein && (
              <p className="text-xs text-muted">
                Ziele setzen unter ⚙️ Einstellungen oder im Chat: „Mein Ziel sind 2600 kcal und 150 g Protein“
              </p>
            )}
          </section>

          <section className={card}>
            <h2 className="mb-3 font-bold">📈 Protein letzte 7 Tage</h2>
            <div className="flex h-28 items-end gap-2">
              {week.map((w) => (
                <div key={w.day} className="flex h-full flex-1 flex-col items-center justify-end gap-1">
                  <span className="text-[10px] text-muted">{w.protein ? round(w.protein) : ""}</span>
                  <div
                    className={`w-full rounded-t-md ${w.day === today ? "bg-accent" : "bg-accent/40"}`}
                    style={{ height: `${(w.protein / maxProtein) * 100}%` }}
                    title={`${round(w.protein)} g Protein · ${round(w.kcal)} kcal`}
                  />
                  <span className={`text-xs ${w.day === today ? "font-bold" : "text-muted"}`}>
                    {weekdayShort(w.day)}
                  </span>
                </div>
              ))}
            </div>
            {goalProtein && <p className="mt-2 text-xs text-muted">Ziel: {goalProtein} g pro Tag</p>}
          </section>
        </div>

        <MealSuggestions />
      </div>
    </div>
  );
}
