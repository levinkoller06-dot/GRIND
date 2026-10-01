import { TZ } from "@/lib/format";
import { dayKey, minutesOfDay } from "@/lib/week";

export type CalEvent = {
  id: string;
  title: string;
  starts_at: string;
  ends_at: string | null;
  all_day: boolean;
  kind: string;
  notes: string | null;
  location: string | null;
  participants: string[] | null;
  /** z. B. "moodle:100526@moodle.bzu.ch" bei importierten Terminen */
  external_id?: string | null;
};

export const KIND_STYLE: Record<string, string> = {
  test: "bg-red-500/15 border-red-500 text-red-700 dark:text-red-300",
  schule: "bg-blue-500/15 border-blue-500 text-blue-700 dark:text-blue-300",
  geburtstag: "bg-pink-500/15 border-pink-500 text-pink-700 dark:text-pink-300",
  termin: "bg-accent/20 border-accent text-foreground",
  sonstiges: "bg-surface-2 border-muted text-foreground",
};

// Alles aus Moodle (Abgaben und Prüfungen) in hellem Orange, wie das helle Grün der App
const MOODLE_STYLE = "bg-orange-400/15 border-orange-400 text-orange-800 dark:text-orange-200";

/** Farbe eines Termins: Moodle-Termine orange, sonst nach Art. */
export function eventStyle(e: Pick<CalEvent, "kind" | "external_id">) {
  if (e.external_id?.startsWith("moodle:")) return MOODLE_STYLE;
  return KIND_STYLE[e.kind] ?? KIND_STYLE.termin;
}

export const time = (iso: string) =>
  new Date(iso).toLocaleTimeString("de-DE", { timeZone: TZ, hour: "2-digit", minute: "2-digit" });

/** Start/Ende in Minuten seit Mitternacht (ohne Ende: 1 Stunde, mindestens 30 Minuten). */
export function eventMinutes(e: CalEvent) {
  const start = minutesOfDay(e.starts_at);
  const end =
    e.ends_at && dayKey(e.ends_at) === dayKey(e.starts_at) ? minutesOfDay(e.ends_at) : start + 60;
  return { start, end: Math.max(end, start + 30) };
}

export function eventTooltip(e: CalEvent) {
  return [
    e.title,
    `${time(e.starts_at)}${e.ends_at ? `–${time(e.ends_at)}` : ""}`,
    e.location && `📍 ${e.location}`,
    e.participants?.length && `👥 ${e.participants.join(", ")}`,
    e.notes,
  ]
    .filter(Boolean)
    .join("\n");
}
