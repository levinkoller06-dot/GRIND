export type Grade = { value: number; weight: number; kind: string; date: string };

export type GradeScale = "ch" | "de";

export const SCALE_LABEL: Record<GradeScale, string> = {
  ch: "Schweiz (6 = beste Note)",
  de: "Deutschland (1 = beste Note)",
};

export function average(grades: Grade[]): number | null {
  const weight = grades.reduce((s, g) => s + Number(g.weight), 0);
  if (!weight) return null;
  return grades.reduce((s, g) => s + Number(g.value) * Number(g.weight), 0) / weight;
}

export function formatGrade(n: number | null) {
  return n === null ? "–" : n.toLocaleString("de-DE", { maximumFractionDigits: 2 });
}

/** Tailwind-Textfarbe: grün = gut, gelb = knapp, rot = ungenügend. */
export function gradeColor(n: number | null, scale: GradeScale) {
  if (n === null) return "text-muted";
  // In "Schweizer Punkte" umrechnen: höher = besser
  const points = scale === "ch" ? n : 7 - n;
  if (points >= 5) return "text-green-500";
  if (points >= 4) return "text-yellow-500";
  return "text-red-500";
}
