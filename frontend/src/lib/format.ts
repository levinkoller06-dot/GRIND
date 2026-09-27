// Später aus dem Profil des Nutzers, vorerst fest.
export const TZ = "Europe/Berlin";

/** Heutiges Datum als YYYY-MM-DD in der Zeitzone des Nutzers. */
export function todayIso() {
  return new Date().toLocaleDateString("sv-SE", { timeZone: TZ });
}

/** UTC-Offset der Zeitzone an einem Tag, z. B. "+02:00" (Sommer) oder "+01:00" (Winter). */
function offset(isoDate: string) {
  const name = new Intl.DateTimeFormat("en-US", { timeZone: TZ, timeZoneName: "longOffset" })
    .formatToParts(new Date(`${isoDate}T12:00:00Z`))
    .find((p) => p.type === "timeZoneName")?.value;
  const match = name?.match(/GMT([+-]\d{2}:\d{2})/);
  return match ? match[1] : "+00:00";
}

/** Beginn (00:00) eines Tages als Zeitstempel mit Offset, für Datenbank-Filter. */
export function dayStart(isoDate: string) {
  return `${isoDate}T00:00:00${offset(isoDate)}`;
}

/** Ende (23:59:59) eines Tages als Zeitstempel mit Offset. */
export function dayEnd(isoDate: string) {
  return `${isoDate}T23:59:59${offset(isoDate)}`;
}

export function formatDay(isoDate: string) {
  return new Date(`${isoDate}T12:00:00`).toLocaleDateString("de-DE", {
    weekday: "short",
    day: "2-digit",
    month: "2-digit",
  });
}

export function formatWhen(p: { datum: string; uhrzeit?: string; ende_uhrzeit?: string }) {
  const day = formatDay(p.datum);
  if (!p.uhrzeit) return `${day} · ganztägig`;
  return `${day} · ${p.uhrzeit}${p.ende_uhrzeit ? `–${p.ende_uhrzeit}` : ""} Uhr`;
}

export const KIND_ICON: Record<string, string> = {
  schule: "🏫",
  termin: "📅",
  test: "📝",
  geburtstag: "🎂",
  sonstiges: "📌",
};
