import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { BackendStatus } from "@/components/BackendStatus";
import { Chat } from "@/components/Chat";
import { TZ, dayEnd, dayStart, formatDay, todayIso } from "@/lib/format";
import { round, sum, type MealItem } from "@/lib/nutrition";
import { daysFor, type PlanDay } from "@/lib/plan";

export default async function StartPage() {
  const supabase = await createClient();
  const { data } = await supabase.auth.getClaims();
  const userId = data?.claims?.sub ?? "";
  const today = todayIso();

  const [
    { data: profile },
    { data: exams },
    { count: openCount },
    { count: eventsToday },
    { data: meals },
    { count: workoutsToday },
    { data: plan },
  ] = await Promise.all([
    supabase
      .from("profiles")
      .select("display_name, goal_kcal, goal_protein_g")
      .eq("id", userId)
      .maybeSingle(),
    supabase.from("exams").select("date, subjects(name)").gte("date", today).order("date").limit(1),
    supabase.from("pending_actions").select("id", { count: "exact", head: true }).eq("status", "open"),
    supabase
      .from("events")
      .select("id", { count: "exact", head: true })
      .gte("starts_at", dayStart(today))
      .lte("starts_at", dayEnd(today)),
    supabase
      .from("meals")
      .select("meal_items(name,amount,kcal,protein_g,carbs_g,fat_g)")
      .gte("eaten_at", dayStart(today))
      .lte("eaten_at", dayEnd(today)),
    supabase.from("workouts").select("id", { count: "exact", head: true }).eq("date", today),
    supabase.from("training_plans").select("days").eq("user_id", userId).maybeSingle(),
  ]);

  const eaten = sum((meals ?? []).flatMap((m) => m.meal_items as unknown as MealItem[]));
  const todayPlan = daysFor((plan?.days ?? []) as PlanDay[], today)[0];
  const nextExam = exams?.[0] as unknown as
    | { date: string; subjects: { name: string } | null }
    | undefined;

  const name = profile?.display_name ?? data?.claims?.email ?? "du";
  const dateLabel = new Date().toLocaleDateString("de-DE", {
    timeZone: TZ,
    weekday: "long",
    day: "numeric",
    month: "long",
  });

  const overview = [
    {
      icon: "💪",
      label: "Training heute",
      value: todayPlan ? todayPlan.titel : "kein Plan",
      sub: workoutsToday ? "✓ erledigt" : todayPlan?.pause ? "Ruhetag" : undefined,
      href: "/gym",
    },
    {
      icon: "🍗",
      label: "Protein",
      value: `${round(eaten.protein_g)}${profile?.goal_protein_g ? ` / ${profile.goal_protein_g}` : ""} g`,
      sub: `${round(eaten.kcal)}${profile?.goal_kcal ? ` / ${profile.goal_kcal}` : ""} kcal`,
      href: "/ernaehrung",
    },
    {
      icon: "📝",
      label: "Nächster Test",
      value: nextExam ? (nextExam.subjects?.name ?? "?") : "keiner",
      sub: nextExam ? formatDay(nextExam.date) : undefined,
      href: "/noten",
    },
    { icon: "📅", label: "Termine heute", value: String(eventsToday ?? 0), href: "/kalender" },
    {
      icon: "✅",
      label: "Zu bestätigen",
      value: String(openCount ?? 0),
      sub: openCount ? "im Chat" : undefined,
    },
  ];

  return (
    <div className="grid gap-4 md:min-h-0 md:flex-1 md:grid-rows-[auto_minmax(0,1fr)_auto] lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)] lg:grid-rows-1">
      <div className="flex flex-col gap-4">
        <header>
          <p className="text-sm text-muted">{dateLabel}</p>
          <h1 className="text-2xl font-black tracking-tight md:text-3xl">Hey {name} 👋</h1>
        </header>

        <section className="grid grid-cols-2 gap-3">
          {overview.map((item) => {
            const content = (
              <>
                <div className="text-xs text-muted">
                  {item.icon} {item.label}
                </div>
                <div className="mt-0.5 truncate text-lg font-bold">{item.value}</div>
                {item.sub && <div className="truncate text-xs text-muted">{item.sub}</div>}
              </>
            );
            const cls = "block rounded-2xl border border-border bg-surface p-3";
            return item.href ? (
              <Link key={item.label} href={item.href} className={`${cls} hover:border-accent`}>
                {content}
              </Link>
            ) : (
              <div key={item.label} className={cls}>
                {content}
              </div>
            );
          })}
        </section>

        <div className="mt-auto hidden lg:block">
          <BackendStatus />
        </div>
      </div>

      <div className="md:min-h-0">
        <Chat />
      </div>
      <div className="lg:hidden">
        <BackendStatus />
      </div>
    </div>
  );
}
