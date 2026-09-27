export type PlanExercise = {
  uebung: string;
  saetze?: number;
  wiederholungen?: number;
  dauer?: string;
  stufe?: string;
  hinweis?: string;
};

export type PlanDay = {
  tag: string;
  titel: string;
  pause?: boolean;
  uebungen: PlanExercise[];
  hinweis?: string;
};

const WEEKDAYS = ["montag", "dienstag", "mittwoch", "donnerstag", "freitag", "samstag", "sonntag"];

export function weekdayName(isoDate: string) {
  return WEEKDAYS[(new Date(`${isoDate}T00:00:00Z`).getUTCDay() + 6) % 7];
}

/** Tage im Plan, die zu einem Datum passen (z. B. "Samstag oder Sonntag" am Samstag). */
export function daysFor(plan: PlanDay[], isoDate: string) {
  const name = weekdayName(isoDate);
  return plan.filter((d) => d.tag.toLowerCase().includes(name));
}

export function describeExercise(e: PlanExercise) {
  const parts = [];
  if (e.saetze && e.wiederholungen) parts.push(`${e.saetze}×${e.wiederholungen}`);
  else if (e.saetze && e.dauer) parts.push(`${e.saetze}×${e.dauer}`);
  else if (e.dauer) parts.push(e.dauer);
  else if (e.saetze) parts.push(`${e.saetze} Sätze`);
  if (e.stufe) parts.push(`Stufe ${e.stufe}`);
  return parts.join(" · ");
}
