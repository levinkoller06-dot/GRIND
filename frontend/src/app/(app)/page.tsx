import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { CountUp, ProgressRing } from "@/components/Animated";
import { BackendStatus } from "@/components/BackendStatus";
import { Chat } from "@/components/Chat";
import { Notifications } from "@/components/Notifications";
import { NowTimeline } from "@/components/NowTimeline";
import type { CalEvent } from "@/lib/events";
import { TZ, dayEnd, dayStart, formatDay, todayIso } from "@/lib/format";
import { sum, type MealItem } from "@/lib/nutrition";
import { daysFor, type PlanDay } from "@/lib/plan";
import { dayKey } from "@/lib/week";

export default async function StartPage() {
  const supabase = await createClient();
  const { data } = await supabase.auth.getClaims();
  const userId = data?.claims?.sub ?? "";
  const today = todayIso();

  const [
    { data: profile },
    { data: exams },
    { data: testEvents },
    { count: openCount },
    { data: meals },
    { count: workoutsToday },
    { data: plan },
    { data: todayEvents },
  ] = await Promise.all([
    supabase
      .from("profiles")
      .select("display_name, goal_kcal, goal_protein_g")
      .eq("id", userId)
      .maybeSingle(),
    supabase.from("exams").select("date, subjects(name)").gte("date", today).order("date").limit(1),
    // Auch Prüfungen aus Moodle zählen als nächster Test
    supabase
      .from("events")
      .select("title, starts_at")
      .eq("kind", "test")
      .gte("starts_at", dayStart(today))
      .order("starts_at")
      .limit(1),
    supabase.from("pending_actions").select("id", { count: "exact", head: true }).eq("status", "open"),
    supabase
      .from("meals")
      .select("meal_items(name,amount,kcal,protein_g,carbs_g,fat_g)")
      .gte("eaten_at", dayStart(today))
      .lte("eaten_at", dayEnd(today)),
    supabase.from("workouts").select("id", { count: "exact", head: true }).eq("date", today),
    supabase.from("training_plans").select("days").eq("user_id", userId).maybeSingle(),
    supabase
      .from("events")
      .select("id,title,starts_at,ends_at,all_day,kind,notes,location,participants,external_id")
      .gte("starts_at", dayStart(today))
      .lte("starts_at", dayEnd(today))
      .order("starts_at"),
  ]);

  const eaten = sum((meals ?? []).flatMap((m) => m.meal_items as unknown as MealItem[]));
  const todayPlan = daysFor((plan?.days ?? []) as PlanDay[], today)[0];
  const exam = exams?.[0] as unknown as { date: string; subjects: { name: string } | null } | undefined;
  const testEvent = testEvents?.[0];
  // Den früheren von beiden nehmen (selbst angelegter Test oder Moodle-Prüfung)
  const nextTest =
    testEvent && (!exam || dayKey(testEvent.starts_at) < exam.date)
      ? { name: testEvent.title, date: dayKey(testEvent.starts_at) }
      : exam && { name: exam.subjects?.name ?? "Test", date: exam.date };

  const events = (todayEvents ?? []) as CalEvent[];
  const name = profile?.display_name ?? data?.claims?.email ?? "du";
  const dateLabel = new Date().toLocaleDateString("de-DE", {
    timeZone: TZ,
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
  const protein = Math.round(eaten.protein_g);
  const proteinGoal = profile?.goal_protein_g ?? 0;

  const tile = "flex min-h-36 flex-col rounded-2xl border bg-surface p-4";
  const label = "text-sm font-medium text-muted";
  const big = "mt-auto truncate font-black tracking-tight text-accent";

  return (
    <div className="grid gap-5 md:min-h-0 md:flex-1 md:grid-rows-[auto_minmax(0,1fr)_auto] lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)] lg:grid-rows-1">
      <div className="stagger flex flex-col gap-5 md:min-h-0 md:overflow-y-auto md:p-1">
        <header className="pt-1">
          <h1 className="text-5xl font-black tracking-tighter md:text-6xl">
            Hey {name} <span className="wave inline-block">👋</span>
          </h1>
          <p className="mt-2 text-sm text-muted">{dateLabel}</p>
        </header>

        <section className="stagger grid grid-cols-2 gap-3 xl:grid-cols-4">
          <Link href="/gym" className={tile}>
            <span className={label}>💪 Training heute</span>
            <span className={`${big} text-3xl`}>
              {workoutsToday ? "✓" : todayPlan ? todayPlan.titel : "–"}
            </span>
            <span className="mt-1 text-xs text-muted">
              {workoutsToday ? "erledigt" : todayPlan?.pause ? "Ruhetag" : todayPlan ? "geplant" : "kein Plan"}
            </span>
          </Link>

          <Link href="/ernaehrung" className={`${tile} items-center`}>
            <span className={`${label} self-start`}>🍗 Protein</span>
            <div className="mt-2">
              <ProgressRing value={proteinGoal ? protein / proteinGoal : 0}>
                <div>
                  <div className="text-sm font-bold">
                    <CountUp to={protein} />
                    {proteinGoal ? <span className="text-muted">/{proteinGoal}</span> : null} g
                  </div>
                  <div className="text-[10px] text-muted">
                    <CountUp to={Math.round(eaten.kcal)} /> kcal
                  </div>
                </div>
              </ProgressRing>
            </div>
          </Link>

          <Link href="/noten" className={tile}>
            <span className={label}>📝 Nächster Test</span>
            <span className={`${big} text-2xl md:text-3xl`} title={nextTest ? nextTest.name : undefined}>
              {nextTest ? nextTest.name : "keiner"}
            </span>
            <span className="mt-1 text-xs text-muted">{nextTest ? formatDay(nextTest.date) : "frei 🎉"}</span>
          </Link>

          <Link href="/kalender" className={tile}>
            <span className={label}>📅 Termine heute</span>
            <CountUp to={events.length} className={`${big} text-5xl`} />
            <span className="mt-1 text-xs text-muted">
              {openCount ? `${openCount} zu bestätigen` : events.length === 1 ? "Termin" : "geplant"}
            </span>
          </Link>
        </section>

        <Notifications />

        <NowTimeline events={events} />

        <div className="mt-auto hidden lg:block">
          <BackendStatus />
        </div>
      </div>

      <div className="page-enter md:min-h-0 [animation-delay:0.15s]">
        <Chat />
      </div>
      <div className="lg:hidden">
        <BackendStatus />
      </div>
    </div>
  );
}
