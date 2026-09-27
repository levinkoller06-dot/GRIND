import { TZ } from "./format";

export const WEEKDAYS_SHORT = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"];

/** Rechnet mit reinen Kalenderdaten (YYYY-MM-DD), ohne Zeitzonen-Fallen. */
export function addDays(isoDate: string, days: number) {
  const d = new Date(`${isoDate}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

/** Montag der Woche, in der `isoDate` liegt. */
export function mondayOf(isoDate: string) {
  const dow = (new Date(`${isoDate}T00:00:00Z`).getUTCDay() + 6) % 7; // Mo = 0
  return addDays(isoDate, -dow);
}

/** ISO-Kalenderwoche. */
export function isoWeek(monday: string) {
  const thursday = new Date(`${addDays(monday, 3)}T00:00:00Z`);
  const jan1 = new Date(Date.UTC(thursday.getUTCFullYear(), 0, 1));
  return Math.floor((thursday.getTime() - jan1.getTime()) / 86_400_000 / 7) + 1;
}

/** Kalendertag (YYYY-MM-DD) eines Zeitstempels in der Zeitzone des Nutzers. */
export function dayKey(iso: string) {
  return new Date(iso).toLocaleDateString("sv-SE", { timeZone: TZ });
}

/** Minuten seit Mitternacht in der Zeitzone des Nutzers. */
export function minutesOfDay(iso: string) {
  const [h, m] = new Date(iso)
    .toLocaleTimeString("de-DE", { timeZone: TZ, hour: "2-digit", minute: "2-digit", hourCycle: "h23" })
    .split(":")
    .map(Number);
  return h * 60 + m;
}

export function weekdayShort(isoDate: string) {
  return WEEKDAYS_SHORT[(new Date(`${isoDate}T00:00:00Z`).getUTCDay() + 6) % 7];
}

export function formatShort(isoDate: string) {
  const [, m, d] = isoDate.split("-");
  return `${d}.${m}.`;
}

export type Placed<T> = T & { start: number; end: number; lane: number; lanes: number };

/** Verteilt sich überschneidende Termine eines Tages auf nebeneinanderliegende Spalten. */
export function layoutDay<T>(items: (T & { start: number; end: number })[]): Placed<T>[] {
  const sorted = items.toSorted((a, b) => a.start - b.start || b.end - a.end);
  const placed: Placed<T>[] = [];
  let cluster: Placed<T>[] = [];
  let clusterEnd = -1;
  let laneEnds: number[] = [];

  const flush = () => {
    const lanes = Math.max(1, laneEnds.length);
    cluster.forEach((p) => (p.lanes = lanes));
    cluster = [];
    laneEnds = [];
  };

  for (const item of sorted) {
    if (item.start >= clusterEnd) flush();
    let lane = laneEnds.findIndex((end) => end <= item.start);
    if (lane === -1) lane = laneEnds.length;
    laneEnds[lane] = item.end;
    const p = { ...item, lane, lanes: 1 } as Placed<T>;
    cluster.push(p);
    placed.push(p);
    clusterEnd = Math.max(clusterEnd, item.end);
  }
  flush();
  return placed;
}
