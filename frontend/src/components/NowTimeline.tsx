"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { eventMinutes, eventStyle, eventTooltip, time, type CalEvent } from "@/lib/events";
import { layoutDay, minutesOfDay } from "@/lib/week";

const ROW_PX = 64;

/** Waagrechte Zeitleiste von heute: letzte, aktuelle und nächste Stunde. */
export function NowTimeline({ events }: { events: CalEvent[] }) {
  // Erst im Browser rechnen, damit Server und Browser nicht verschiedene Zeiten anzeigen
  const [now, setNow] = useState<number | null>(null);
  useEffect(() => {
    const tick = () => setNow(minutesOfDay(new Date().toISOString()));
    tick();
    const id = setInterval(tick, 30_000);
    return () => clearInterval(id);
  }, []);

  const hour = Math.floor((now ?? 0) / 60);
  const firstHour = Math.max(0, Math.min(hour - 1, 21));
  const hours = [firstHour, firstHour + 1, firstHour + 2, firstHour + 3];
  const from = firstHour * 60;
  const to = from + 180;
  const pct = (minutes: number) => `${((minutes - from) / (to - from)) * 100}%`;

  const allDay = events.filter((e) => e.all_day);
  // Sich überschneidende Termine kommen in eigene Zeilen untereinander
  const visible = layoutDay(
    events
      .filter((e) => !e.all_day)
      .map((e) => ({ ...e, ...eventMinutes(e) }))
      .filter((e) => e.end > from && e.start < to),
  );
  const rows = Math.max(1, ...visible.map((e) => e.lanes));

  return (
    <Link href="/kalender" className="block rounded-2xl border bg-surface p-5">
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="text-lg font-bold tracking-tight">Jetzt</h2>
        {allDay.length > 0 && (
          <span className="truncate text-xs text-muted">🗓️ {allDay.map((e) => e.title).join(" · ")}</span>
        )}
      </div>

      {now === null ? (
        <div style={{ height: 56 + rows * ROW_PX }} />
      ) : (
        <div className="relative mt-6">
          {/* Stunden und Viertelstunden-Striche */}
          <div className="relative h-8 border-b border-border">
            {hours.map((h, i) => (
              <span
                key={h}
                className="absolute top-0 -translate-x-1/2 text-xs text-muted tabular-nums first:translate-x-0 last:-translate-x-full"
                style={{ left: `${(i / 3) * 100}%` }}
              >
                {String(h % 24).padStart(2, "0")}:00
              </span>
            ))}
            {Array.from({ length: 13 }, (_, i) => (
              <span
                key={i}
                className={`absolute bottom-0 w-px bg-border ${i % 4 === 0 ? "h-3" : "h-1.5"}`}
                style={{ left: `${(i / 12) * 100}%` }}
              />
            ))}
          </div>

          <div className="relative mt-3" style={{ height: rows * ROW_PX }}>
            {visible.map((e) => {
              const start = Math.max(e.start, from);
              const end = Math.min(e.end, to);
              return (
                <div
                  key={e.id}
                  title={eventTooltip(e)}
                  className={`absolute overflow-hidden rounded-xl border-l-[3px] px-2.5 py-1.5 text-xs leading-tight shadow-sm transition-transform duration-300 hover:-translate-y-0.5 ${eventStyle(e)}`}
                  style={{
                    left: `calc(${pct(start)} + 2px)`,
                    width: `calc(${((end - start) / (to - from)) * 100}% - 4px)`,
                    top: e.lane * ROW_PX,
                    height: ROW_PX - 6,
                  }}
                >
                  <div className="truncate tabular-nums opacity-70">
                    {time(e.starts_at)}
                    {e.ends_at && ` – ${time(e.ends_at)}`}
                  </div>
                  <div className="truncate text-sm font-semibold">{e.title}</div>
                  {(e.location || e.participants?.length) && (
                    <div className="truncate opacity-70">
                      {e.location ? `📍 ${e.location}` : `👥 ${e.participants!.join(", ")}`}
                    </div>
                  )}
                </div>
              );
            })}
            {visible.length === 0 && (
              <p className="absolute inset-0 grid place-items-center text-sm text-muted">Gerade nichts los ✨</p>
            )}
          </div>

          {/* Jetzt-Linie mit Etikett */}
          <div className="pointer-events-none absolute -top-6 bottom-0 z-10" style={{ left: pct(now) }}>
            <span className="now-pulse absolute top-0 -translate-x-1/2 rounded-md bg-red-500 px-1.5 py-0.5 text-[10px] font-semibold text-white shadow">
              Jetzt
            </span>
            <span className="absolute top-5 bottom-0 w-0.5 -translate-x-1/2 rounded-full bg-red-500" />
          </div>
        </div>
      )}
    </Link>
  );
}
