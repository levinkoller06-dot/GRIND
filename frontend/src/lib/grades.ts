export type Grade = { value: number; weight: number; kind: string; date: string };

export function average(grades: Grade[]): number | null {
  const weight = grades.reduce((s, g) => s + Number(g.weight), 0);
  if (!weight) return null;
  return grades.reduce((s, g) => s + Number(g.value) * Number(g.weight), 0) / weight;
}

export function formatGrade(n: number | null) {
  return n === null ? "–" : n.toLocaleString("de-DE", { maximumFractionDigits: 2 });
}
