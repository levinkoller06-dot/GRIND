import { DeleteButton } from "@/components/DeleteButton";
import { TABS } from "@/components/tabs";
import { createClient } from "@/lib/supabase/server";
import { TZ, dayEnd, dayStart, formatDay, todayIso } from "@/lib/format";
import { MEAL_LABEL, round, sum, type Meal } from "@/lib/nutrition";
import { addDays, dayKey, weekdayShort } from "@/lib/week";
import { deleteMeal, deleteWorkout } from "./actions";

const tab = TABS.find((t) => t.href === "/gym")!;

type Entry = {
  exercise: string;
  sets: number | null;
  reps: number | null;
  weight_kg: number | null;
  duration_min: number | null;
  distance_km: number | null;
};

type Workout = { id: string; date: string; title: string | null; notes: string | null; workout_entries: Entry[] };

function describeEntry(e: Entry) {
  const parts = [];
  if (e.sets && e.reps) parts.push(`${e.sets}×${e.reps}`);
  else if (e.reps) parts.push(`${e.reps} Wdh.`);
  else if (e.sets) parts.push(`${e.sets} Sätze`);
  if (e.weight_kg) parts.push(`${Number(e.weight_kg)} kg`);
  if (e.distance_km) parts.push(`${Number(e.distance_km)} km`);
  if (e.duration_min) parts.push(`${Number(e.duration_min)} min`);
  return parts.join(" · ");
}

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
      <div className="mt-1 h-2 overflow-hidden rounded-full bg-surface-2">
        <div className="h-full rounded-full bg-accent" style={{ width: `${goal ? pct : 0}%` }} />
      </div>
    </div>
  );
}

export default async function GymPage() {
  const supabase = await createClient();
  const { data: claims } = await supabase.auth.getClaims();
  const today = todayIso();
  const weekStart = addDays(today, -6);

  const [{ data: profile }, { data: mealData }, { data: workoutData }, { data: allEntries }] =
    await Promise.all([
      supabase
        .from("profiles")
        .select("goal_kcal, goal_protein_g")
        .eq("id", claims?.claims?.sub ?? "")
        .maybeSingle(),
      supabase
        .from("meals")
        .select("id,eaten_at,meal_type,description,from_photo,meal_items(name,amount,kcal,protein_g,carbs_g,fat_g)")
        .gte("eaten_at", dayStart(weekStart))
        .lte("eaten_at", dayEnd(today))
        .order("eaten_at"),
      supabase
        .from("workouts")
        .select("id,date,title,notes,workout_entries(exercise,sets,reps,weight_kg,duration_min,distance_km)")
        .gte("date", addDays(today, -13))
        .order("date", { ascending: false })
        .order("created_at", { ascending: false }),
      supabase.from("workout_entries").select("exercise,reps,weight_kg,distance_km"),
    ]);

  const meals = (mealData ?? []) as Meal[];
  const workouts = (workoutData ?? []) as Workout[];
  const todayMeals = meals.filter((m) => dayKey(m.eaten_at) === today);
  const todaySum = sum(todayMeals.flatMap((m) => m.meal_items));
  const goalKcal = profile?.goal_kcal ?? null;
  const goalProtein = profile?.goal_protein_g ?? null;

  // Protein der letzten 7 Tage
  const week = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i)).map((d) => ({
    day: d,
    protein: sum(meals.filter((m) => dayKey(m.eaten_at) === d).flatMap((m) => m.meal_items)).protein_g,
    trained: workouts.some((w) => w.date === d),
  }));
  const maxProtein = Math.max(goalProtein ?? 0, ...week.map((w) => w.protein), 1);

  // Bestwerte pro Übung
  const records = new Map<string, { name: string; weight: number; reps: number; distance: number }>();
  for (const e of (allEntries ?? []) as Entry[]) {
    const key = e.exercise.trim().toLowerCase();
    const r = records.get(key) ?? { name: e.exercise, weight: 0, reps: 0, distance: 0 };
    r.weight = Math.max(r.weight, Number(e.weight_kg ?? 0));
    r.reps = Math.max(r.reps, Number(e.reps ?? 0));
    r.distance = Math.max(r.distance, Number(e.distance_km ?? 0));
    records.set(key, r);
  }

  const time = (iso: string) =>
    new Date(iso).toLocaleTimeString("de-DE", { timeZone: TZ, hour: "2-digit", minute: "2-digit" });

  const card = "rounded-2xl border border-border bg-surface p-4";

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-black tracking-tight">
          {tab.icon} {tab.label}
        </h1>
        <p className="text-muted">{tab.description}</p>
      </header>

      {/* Heute gegessen */}
      <section className={`${card} space-y-3`}>
        <h2 className="font-bold">🍗 Heute</h2>
        <Progress label="Kalorien" value={todaySum.kcal} goal={goalKcal} unit="kcal" />
        <Progress label="Protein" value={todaySum.protein_g} goal={goalProtein} unit="g" />
        <div className="flex gap-4 text-xs text-muted">
          <span>KH {round(todaySum.carbs_g)} g</span>
          <span>Fett {round(todaySum.fat_g)} g</span>
          {!goalKcal && !goalProtein && <span>Ziele setzen: Einstellungen oder „Mein Ziel sind 150 g Protein“</span>}
        </div>

        {todayMeals.length === 0 ? (
          <p className="text-sm text-muted">Noch nichts eingetragen. Schreib dem Gehirn, was du gegessen hast, oder schick ein 📷 Foto.</p>
        ) : (
          <ul className="divide-y divide-border">
            {todayMeals.map((m) => {
              const s = sum(m.meal_items);
              return (
                <li key={m.id} className="flex items-start gap-2 py-2">
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-medium">
                      {MEAL_LABEL[m.meal_type] ?? m.meal_type} · {time(m.eaten_at)}
                      {m.from_photo && " · 📷"}
                    </div>
                    <div className="truncate text-sm text-muted">
                      {m.description ?? m.meal_items.map((i) => i.name).join(", ")}
                    </div>
                    <div className="text-xs text-muted">
                      {round(s.kcal)} kcal · {round(s.protein_g)} g Protein
                    </div>
                  </div>
                  <DeleteButton action={deleteMeal.bind(null, m.id)} label="Mahlzeit" />
                </li>
              );
            })}
          </ul>
        )}
      </section>

      {/* Woche */}
      <section className={card}>
        <h2 className="mb-3 font-bold">📈 Letzte 7 Tage</h2>
        <div className="flex h-32 items-end gap-2">
          {week.map((w) => (
            <div key={w.day} className="flex h-full flex-1 flex-col items-center justify-end gap-1">
              <span className="text-[10px] text-muted">{w.protein ? round(w.protein) : ""}</span>
              <div
                className={`w-full rounded-t-md ${w.day === today ? "bg-accent" : "bg-accent/40"}`}
                style={{ height: `${(w.protein / maxProtein) * 100}%` }}
                title={`${round(w.protein)} g Protein`}
              />
              <span className={`text-xs ${w.day === today ? "font-bold" : "text-muted"}`}>
                {weekdayShort(w.day)}
              </span>
              <span className="text-xs">{w.trained ? "💪" : "·"}</span>
            </div>
          ))}
        </div>
        <p className="mt-2 text-xs text-muted">
          Balken = Protein in g{goalProtein ? ` (Ziel ${goalProtein} g)` : ""} · 💪 = trainiert ·{" "}
          {week.filter((w) => w.trained).length} Trainings diese Woche
        </p>
      </section>

      {/* Trainings */}
      <section className="space-y-2">
        <h2 className="text-sm font-bold text-muted">💪 Trainings (letzte 14 Tage)</h2>
        {workouts.length === 0 && (
          <div className="rounded-2xl border border-dashed border-border bg-surface p-6 text-center text-sm text-muted">
            Noch keine Trainings. Sag dem Gehirn z. B. „Hab 3×10 Liegestütze und 4×8 Bankdrücken mit 60 kg gemacht“.
          </div>
        )}
        {workouts.map((w) => (
          <div key={w.id} className={`${card} flex items-start gap-2`}>
            <div className="min-w-0 flex-1">
              <div className="font-bold">
                {formatDay(w.date)}
                {w.title && ` · ${w.title}`}
              </div>
              <ul className="mt-1 space-y-0.5 text-sm">
                {w.workout_entries.map((e, i) => (
                  <li key={i}>
                    <span className="font-medium">{e.exercise}</span>{" "}
                    <span className="text-muted">{describeEntry(e)}</span>
                  </li>
                ))}
              </ul>
              {w.notes && <div className="mt-1 text-sm text-muted">{w.notes}</div>}
            </div>
            <DeleteButton action={deleteWorkout.bind(null, w.id)} label="Training" />
          </div>
        ))}
      </section>

      {/* Rekorde */}
      {records.size > 0 && (
        <section className={card}>
          <h2 className="mb-2 font-bold">🏆 Rekorde</h2>
          <ul className="divide-y divide-border text-sm">
            {[...records.values()]
              .toSorted((a, b) => a.name.localeCompare(b.name))
              .map((r) => (
                <li key={r.name} className="flex justify-between py-1.5">
                  <span>{r.name}</span>
                  <span className="font-bold">
                    {[
                      r.weight ? `${r.weight} kg` : null,
                      !r.weight && r.reps ? `${r.reps} Wdh.` : null,
                      r.distance ? `${r.distance} km` : null,
                    ]
                      .filter(Boolean)
                      .join(" · ") || "–"}
                  </span>
                </li>
              ))}
          </ul>
        </section>
      )}
    </div>
  );
}
