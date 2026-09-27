import Link from "next/link";
import { TABS } from "@/components/tabs";
import { createClient } from "@/lib/supabase/server";
import { KIND_ICON, TZ, dayEnd, dayStart, todayIso } from "@/lib/format";
import {
  WEEKDAYS_SHORT,
  addDays,
  dayKey,
  formatShort,
  isoWeek,
  layoutDay,
  minutesOfDay,
  mondayOf,
} from "@/lib/week";

const tab = TABS.find((t) => t.href === "/kalender")!;

type Event = {
  id: string;
  title: string;
  starts_at: string;
  ends_at: string | null;
  all_day: boolean;
  kind: string;
  notes: string | null;
  location: string | null;
  participants: string[];
};

const HOUR_PX = 48;

const KIND_STYLE: Record<string, string> = {
  test: "bg-red-500/15 border-red-500 text-red-700 dark:text-red-300",
  schule: "bg-blue-500/15 border-blue-500 text-blue-700 dark:text-blue-300",
  geburtstag: "bg-pink-500/15 border-pink-500 text-pink-700 dark:text-pink-300",
  termin: "bg-accent/20 border-accent text-foreground",
  sonstiges: "bg-surface-2 border-muted text-foreground",
};

const time = (iso: string) =>
  new Date(iso).toLocaleTimeString("de-DE", { timeZone: TZ, hour: "2-digit", minute: "2-digit" });

function when(e: Event) {
  if (e.all_day) return "ganztägig";
  return `${time(e.starts_at)}${e.ends_at ? `–${time(e.ends_at)}` : ""}`;
}

export default async function KalenderPage({ searchParams }: PageProps<"/kalender">) {
  // Nur diese, letzte und nächste Woche
  const offset = Math.max(-1, Math.min(1, Number((await searchParams).w) || 0));
  const today = todayIso();
  const monday = addDays(mondayOf(today), offset * 7);
  const days = Array.from({ length: 7 }, (_, i) => addDays(monday, i));

  const supabase = await createClient();
  const { data } = await supabase
    .from("events")
    .select("id,title,starts_at,ends_at,all_day,kind,notes,location,participants")
    .gte("starts_at", dayStart(days[0]))
    .lte("starts_at", dayEnd(days[6]))
    .order("starts_at");
  const events = (data ?? []) as Event[];

  const timed = events
    .filter((e) => !e.all_day)
    .map((e) => {
      const start = minutesOfDay(e.starts_at);
      const end =
        e.ends_at && dayKey(e.ends_at) === dayKey(e.starts_at) ? minutesOfDay(e.ends_at) : start + 60;
      return { ...e, day: dayKey(e.starts_at), start, end: Math.max(end, start + 30) };
    });

  // Sichtbarer Bereich: 7–21 Uhr, bei Bedarf erweitert
  const firstHour = Math.min(7, ...timed.map((e) => Math.floor(e.start / 60)));
  const lastHour = Math.max(21, ...timed.map((e) => Math.ceil(e.end / 60)));
  const hours = Array.from({ length: lastHour - firstHour }, (_, i) => firstHour + i);

  const nowMinutes = minutesOfDay(new Date().toISOString());
  const nav = "rounded-lg border border-border px-3 py-1.5 text-sm font-medium";

  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-3xl font-black tracking-tight">
          {tab.icon} {tab.label}
        </h1>
        <p className="text-muted">{tab.description}</p>
      </header>

      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="font-bold">
          KW {isoWeek(monday)} · {formatShort(days[0])} – {formatShort(days[6])}
        </div>
        <div className="flex gap-1">
          {offset > -1 ? (
            <Link href={`/kalender?w=${offset - 1}`} className={`${nav} hover:bg-surface-2`}>
              ←
            </Link>
          ) : (
            <span className={`${nav} opacity-30`}>←</span>
          )}
          <Link
            href="/kalender"
            className={`${nav} ${offset === 0 ? "bg-accent text-accent-fg border-accent" : "hover:bg-surface-2"}`}
          >
            Diese Woche
          </Link>
          {offset < 1 ? (
            <Link href={`/kalender?w=${offset + 1}`} className={`${nav} hover:bg-surface-2`}>
              →
            </Link>
          ) : (
            <span className={`${nav} opacity-30`}>→</span>
          )}
        </div>
      </div>

      <div className="overflow-x-auto rounded-2xl border border-border bg-surface">
        <div className="min-w-[640px]">
          {/* Kopfzeile mit Tagen */}
          <div className="grid grid-cols-[3rem_repeat(7,1fr)] border-b border-border">
            <div />
            {days.map((d, i) => (
              <div
                key={d}
                className={`py-2 text-center text-xs ${d === today ? "font-bold text-accent" : "text-muted"}`}
              >
                {WEEKDAYS_SHORT[i]}
                <div
                  className={`mx-auto mt-0.5 flex size-7 items-center justify-center rounded-full text-sm ${
                    d === today ? "bg-accent text-accent-fg" : "text-foreground"
                  }`}
                >
                  {Number(d.slice(8))}
                </div>
              </div>
            ))}
          </div>

          {/* Ganztägige Termine */}
          {events.some((e) => e.all_day) && (
            <div className="grid grid-cols-[3rem_repeat(7,1fr)] border-b border-border">
              <div className="py-1 pr-1 text-right text-[10px] text-muted">ganzt.</div>
              {days.map((d) => (
                <div key={d} className="space-y-0.5 border-l border-border p-0.5">
                  {events
                    .filter((e) => e.all_day && dayKey(e.starts_at) === d)
                    .map((e) => (
                      <div
                        key={e.id}
                        title={e.title}
                        className={`truncate rounded border-l-2 px-1 text-[11px] font-medium ${KIND_STYLE[e.kind] ?? KIND_STYLE.termin}`}
                      >
                        {KIND_ICON[e.kind]} {e.title}
                      </div>
                    ))}
                </div>
              ))}
            </div>
          )}

          {/* Stundenraster */}
          <div className="grid grid-cols-[3rem_repeat(7,1fr)]">
            <div>
              {hours.map((h) => (
                <div key={h} style={{ height: HOUR_PX }} className="pr-1 text-right text-[10px] text-muted">
                  <span className="relative -top-1.5">{String(h).padStart(2, "0")}:00</span>
                </div>
              ))}
            </div>
            {days.map((d) => (
              <div key={d} className="relative border-l border-border">
                {hours.map((h) => (
                  <div key={h} style={{ height: HOUR_PX }} className="border-t border-border/60" />
                ))}
                {d === today && nowMinutes >= firstHour * 60 && nowMinutes <= lastHour * 60 && (
                  <div
                    className="absolute inset-x-0 z-10 border-t-2 border-red-500"
                    style={{ top: ((nowMinutes - firstHour * 60) / 60) * HOUR_PX }}
                  />
                )}
                {layoutDay(timed.filter((e) => e.day === d)).map((e) => (
                  <div
                    key={e.id}
                    title={[e.title, when(e), e.location, e.participants.join(", ")]
                      .filter(Boolean)
                      .join(" · ")}
                    className={`absolute overflow-hidden rounded-md border-l-2 px-1 py-0.5 text-[11px] leading-tight ${KIND_STYLE[e.kind] ?? KIND_STYLE.termin}`}
                    style={{
                      top: ((e.start - firstHour * 60) / 60) * HOUR_PX + 1,
                      height: Math.max(((e.end - e.start) / 60) * HOUR_PX - 2, 18),
                      left: `calc(${(e.lane / e.lanes) * 100}% + 2px)`,
                      width: `calc(${100 / e.lanes}% - 4px)`,
                    }}
                  >
                    <div className="truncate font-semibold">{e.title}</div>
                    <div className="truncate opacity-80">{time(e.starts_at)}</div>
                    {e.location && <div className="truncate opacity-80">📍 {e.location}</div>}
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Details der Woche (vor allem fürs Handy) */}
      <section className="space-y-2">
        <h2 className="text-sm font-bold text-muted">Diese Woche im Detail</h2>
        {events.length === 0 && (
          <div className="rounded-2xl border border-dashed border-border bg-surface p-6 text-center text-sm text-muted">
            Keine Termine. Sag dem Gehirn z. B. „Samstag 20 Uhr Kino mit Tim im Pathé“.
          </div>
        )}
        {events.map((e) => {
          const d = dayKey(e.starts_at);
          return (
            <div key={e.id} className="flex gap-3 rounded-2xl border border-border bg-surface p-3">
              <div className="w-10 shrink-0 text-center">
                <div className="text-xs text-muted">
                  {WEEKDAYS_SHORT[(new Date(`${d}T00:00:00Z`).getUTCDay() + 6) % 7]}
                </div>
                <div className="font-bold">{Number(d.slice(8))}</div>
              </div>
              <div className="min-w-0">
                <div className="font-bold">
                  {KIND_ICON[e.kind]} {e.title}
                </div>
                <div className="text-sm text-muted">{when(e)}</div>
                {e.location && <div className="text-sm text-muted">📍 {e.location}</div>}
                {e.participants.length > 0 && (
                  <div className="text-sm text-muted">👥 {e.participants.join(", ")}</div>
                )}
                {e.notes && <div className="text-sm text-muted">{e.notes}</div>}
              </div>
            </div>
          );
        })}
      </section>
    </div>
  );
}
