import { createClient } from "@/lib/supabase/server";
import { BackendStatus } from "@/components/BackendStatus";
import { Chat } from "@/components/Chat";
import { TZ, dayEnd, dayStart, formatDay, todayIso } from "@/lib/format";

export default async function StartPage() {
  const supabase = await createClient();
  const { data } = await supabase.auth.getClaims();
  const userId = data?.claims?.sub;
  const today = todayIso();

  const [{ data: profile }, { data: exams }, { count: openCount }, { count: eventsToday }] =
    await Promise.all([
      supabase.from("profiles").select("display_name").eq("id", userId ?? "").maybeSingle(),
      supabase.from("exams").select("date, subjects(name)").gte("date", today).order("date").limit(1),
      supabase
        .from("pending_actions")
        .select("id", { count: "exact", head: true })
        .eq("status", "open"),
      supabase
        .from("events")
        .select("id", { count: "exact", head: true })
        .gte("starts_at", dayStart(today))
        .lte("starts_at", dayEnd(today)),
    ]);

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
      icon: "📝",
      label: "Nächster Test",
      value: nextExam ? `${nextExam.subjects?.name ?? "?"} · ${formatDay(nextExam.date)}` : "keiner",
    },
    { icon: "📅", label: "Termine heute", value: String(eventsToday ?? 0) },
    { icon: "✅", label: "Zu bestätigen", value: String(openCount ?? 0) },
    { icon: "💪", label: "Training heute", value: "–" },
  ];

  return (
    <div className="space-y-6">
      <header>
        <p className="text-sm text-muted">{dateLabel}</p>
        <h1 className="text-3xl font-black tracking-tight">Hey {name} 👋</h1>
      </header>

      <section className="grid grid-cols-2 gap-3">
        {overview.map((item) => (
          <div key={item.label} className="rounded-2xl border border-border bg-surface p-4">
            <div className="text-sm text-muted">
              {item.icon} {item.label}
            </div>
            <div className="mt-1 truncate text-lg font-bold">{item.value}</div>
          </div>
        ))}
      </section>

      <Chat />

      <BackendStatus />
    </div>
  );
}
