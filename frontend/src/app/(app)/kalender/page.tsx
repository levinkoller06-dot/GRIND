import { TABS } from "@/components/tabs";
import { createClient } from "@/lib/supabase/server";
import { KIND_ICON, TZ, dayStart, todayIso } from "@/lib/format";

const tab = TABS.find((t) => t.href === "/kalender")!;

type Event = {
  id: string;
  title: string;
  starts_at: string;
  ends_at: string | null;
  all_day: boolean;
  kind: string;
  notes: string | null;
};

const time = (iso: string) =>
  new Date(iso).toLocaleTimeString("de-DE", { timeZone: TZ, hour: "2-digit", minute: "2-digit" });

export default async function KalenderPage() {
  const supabase = await createClient();
  const { data } = await supabase
    .from("events")
    .select("id,title,starts_at,ends_at,all_day,kind,notes")
    .gte("starts_at", dayStart(todayIso()))
    .order("starts_at")
    .limit(100);

  const byDay = new Map<string, Event[]>();
  for (const e of (data ?? []) as Event[]) {
    const day = new Date(e.starts_at).toLocaleDateString("de-DE", {
      timeZone: TZ,
      weekday: "long",
      day: "numeric",
      month: "long",
    });
    byDay.set(day, [...(byDay.get(day) ?? []), e]);
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-black tracking-tight">
          {tab.icon} {tab.label}
        </h1>
        <p className="text-muted">{tab.description}</p>
      </header>

      {byDay.size === 0 && (
        <div className="rounded-2xl border border-dashed border-border bg-surface p-8 text-center text-muted">
          Keine Termine. Sag dem Gehirn z. B. „Dienstag 15 Uhr Zahnarzt“.
        </div>
      )}

      {[...byDay].map(([day, events]) => (
        <section key={day}>
          <h2 className="mb-2 text-sm font-bold text-muted">{day}</h2>
          <ul className="space-y-2">
            {events.map((e) => (
              <li key={e.id} className="flex gap-3 rounded-2xl border border-border bg-surface p-4">
                <span className="text-xl" aria-hidden>
                  {KIND_ICON[e.kind] ?? "📅"}
                </span>
                <div>
                  <div className="font-bold">{e.title}</div>
                  <div className="text-sm text-muted">
                    {e.all_day
                      ? "ganztägig"
                      : `${time(e.starts_at)}${e.ends_at ? `–${time(e.ends_at)}` : ""} Uhr`}
                  </div>
                  {e.notes && <div className="text-sm text-muted">{e.notes}</div>}
                </div>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
