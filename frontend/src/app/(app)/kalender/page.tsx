import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { TABS } from "@/components/tabs";
import { eventMinutes, eventStyle, eventTooltip, time, type CalEvent } from "@/lib/events";
import { createClient } from "@/lib/supabase/server";
import { KIND_ICON, dayEnd, dayStart, todayIso } from "@/lib/format";
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

export default async function KalenderPage({ searchParams }: PageProps<"/kalender">) {
  // Nur diese, letzte und nächste Woche
  const offset = Math.max(-1, Math.min(1, Number((await searchParams).w) || 0));
  const today = todayIso();
  const monday = addDays(mondayOf(today), offset * 7);
  const days = Array.from({ length: 7 }, (_, i) => addDays(monday, i));

  const supabase = await createClient();
  const { data } = await supabase
    .from("events")
    .select("*")
    .gte("starts_at", dayStart(days[0]))
    .lte("starts_at", dayEnd(days[6]))
    .order("starts_at");
  const events = (data ?? []) as CalEvent[];

  const timed = events
    .filter((e) => !e.all_day)
    .map((e) => ({ ...e, day: dayKey(e.starts_at), ...eventMinutes(e) }));

  // Sichtbarer Bereich: 7–21 Uhr, bei Bedarf erweitert. Positionen in Prozent,
  // damit das Raster immer genau in den Bildschirm passt.
  const firstHour = Math.min(7, ...timed.map((e) => Math.floor(e.start / 60)));
  const lastHour = Math.max(21, ...timed.map((e) => Math.ceil(e.end / 60)));
  const hours = Array.from({ length: lastHour - firstHour }, (_, i) => firstHour + i);
  const total = (lastHour - firstHour) * 60;
  const pct = (minutes: number) => `${((minutes - firstHour * 60) / total) * 100}%`;

  const nowMinutes = minutesOfDay(new Date().toISOString());
  const hasAllDay = events.some((e) => e.all_day);
  const nav = "rounded-lg border border-border px-3 py-1.5 text-sm font-medium";

  return (
    <div className="flex flex-col md:min-h-0 md:flex-1">
      <PageHeader tab={tab}>
        <div className="flex items-center gap-2">
          <span className="mr-1 text-sm font-bold">
            KW {isoWeek(monday)} · {formatShort(days[0])}–{formatShort(days[6])}
          </span>
          {offset > -1 ? (
            <Link href={`/kalender?w=${offset - 1}`} className={`${nav} hover:bg-surface-2`}>
              ←
            </Link>
          ) : (
            <span className={`${nav} opacity-30`}>←</span>
          )}
          <Link
            href="/kalender"
            className={`${nav} ${offset === 0 ? "border-accent bg-accent text-accent-fg" : "hover:bg-surface-2"}`}
          >
            Heute
          </Link>
          {offset < 1 ? (
            <Link href={`/kalender?w=${offset + 1}`} className={`${nav} hover:bg-surface-2`}>
              →
            </Link>
          ) : (
            <span className={`${nav} opacity-30`}>→</span>
          )}
        </div>
      </PageHeader>

      <div className="flex flex-col overflow-x-auto rounded-2xl border border-border bg-surface md:min-h-0 md:flex-1">
        <div className="flex min-w-[640px] flex-1 flex-col md:min-h-0">
          {/* Kopfzeile mit Tagen */}
          <div className="grid grid-cols-[3rem_repeat(7,1fr)] border-b border-border">
            <div />
            {days.map((d, i) => (
              <div
                key={d}
                className={`flex items-center justify-center gap-1.5 py-2 text-xs ${d === today ? "font-bold text-accent" : "text-muted"}`}
              >
                {WEEKDAYS_SHORT[i]}
                <span
                  className={`flex size-6 items-center justify-center rounded-full text-sm ${
                    d === today ? "bg-accent text-accent-fg" : "text-foreground"
                  }`}
                >
                  {Number(d.slice(8))}
                </span>
              </div>
            ))}
          </div>

          {/* Ganztägige Termine */}
          {hasAllDay && (
            <div className="grid grid-cols-[3rem_repeat(7,1fr)] border-b border-border">
              <div className="py-1 pr-1 text-right text-[10px] text-muted">ganzt.</div>
              {days.map((d) => (
                <div key={d} className="space-y-0.5 border-l border-border p-0.5">
                  {events
                    .filter((e) => e.all_day && dayKey(e.starts_at) === d)
                    .map((e) => (
                      <div
                        key={e.id}
                        title={[e.title, e.location, e.notes].filter(Boolean).join(" · ")}
                        className={`truncate rounded border-l-2 px-1 text-[11px] font-medium ${eventStyle(e)}`}
                      >
                        {KIND_ICON[e.kind]} {e.title}
                      </div>
                    ))}
                </div>
              ))}
            </div>
          )}

          {/* Stundenraster */}
          <div className="grid h-[640px] flex-1 grid-cols-[3rem_repeat(7,1fr)] md:h-auto md:min-h-0">
            <div className="flex flex-col">
              {hours.map((h) => (
                <div key={h} className="flex-1 pr-1 text-right text-[10px] text-muted">
                  <span className="relative -top-1.5">{String(h).padStart(2, "0")}:00</span>
                </div>
              ))}
            </div>
            {days.map((d) => (
              <div key={d} className={`relative flex flex-col border-l border-border ${d === today ? "bg-accent/5" : ""}`}>
                {hours.map((h) => (
                  <div key={h} className="flex-1 border-t border-border/60" />
                ))}
                {d === today && nowMinutes >= firstHour * 60 && nowMinutes <= lastHour * 60 && (
                  <div className="absolute inset-x-0 z-10 border-t-2 border-red-500" style={{ top: pct(nowMinutes) }} />
                )}
                {layoutDay(timed.filter((e) => e.day === d)).map((e) => (
                  <div
                    key={e.id}
                    title={eventTooltip(e)}
                    className={`cal-event absolute overflow-hidden rounded-md border-l-2 px-1 py-0.5 text-[11px] leading-tight ${eventStyle(e)}`}
                    style={{
                      top: `calc(${pct(e.start)} + 1px)`,
                      height: `calc(${((e.end - e.start) / total) * 100}% - 2px)`,
                      minHeight: 16,
                      left: `calc(${(e.lane / e.lanes) * 100}% + 2px)`,
                      width: `calc(${100 / e.lanes}% - 4px)`,
                    }}
                  >
                    <div className="truncate">
                      <span className="font-semibold">{e.title}</span>
                      <span className="cal-inline-time opacity-80"> · {time(e.starts_at)}</span>
                    </div>
                    <div className="cal-second-line truncate opacity-80">
                      {time(e.starts_at)}
                      {e.location && ` · 📍 ${e.location}`}
                    </div>
                    {e.participants && e.participants.length > 0 && (
                      <div className="cal-people truncate opacity-80">👥 {e.participants.join(", ")}</div>
                    )}
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      </div>

      {events.length === 0 && (
        <p className="mt-2 text-center text-xs text-muted">
          Keine Termine diese Woche. Sag dem Gehirn z. B. „Samstag 20 Uhr Kino mit Tim im Pathé“.
        </p>
      )}
    </div>
  );
}
