import { TABS } from "@/components/tabs";
import { createClient } from "@/lib/supabase/server";
import { formatDay, todayIso } from "@/lib/format";
import { average, formatGrade, type Grade } from "@/lib/grades";

const tab = TABS.find((t) => t.href === "/noten")!;

type Subject = { id: string; name: string; grades: Grade[] };
type Exam = { id: string; date: string; topics: string | null; subjects: { name: string } | null };

export default async function NotenPage() {
  const supabase = await createClient();

  const [{ data: subjects }, { data: exams }] = await Promise.all([
    supabase.from("subjects").select("id,name,grades(value,weight,kind,date)").order("name"),
    supabase
      .from("exams")
      .select("id,date,topics,subjects(name)")
      .gte("date", todayIso())
      .order("date"),
  ]);

  const list = (subjects ?? []) as Subject[];
  const upcoming = (exams ?? []) as unknown as Exam[];
  const all = list.flatMap((s) => s.grades);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-black tracking-tight">
          {tab.icon} {tab.label}
        </h1>
        <p className="text-muted">{tab.description}</p>
      </header>

      {upcoming.length > 0 && (
        <section>
          <h2 className="mb-2 text-sm font-bold text-muted">Anstehende Tests</h2>
          <ul className="space-y-2">
            {upcoming.map((e) => (
              <li key={e.id} className="rounded-2xl border border-border bg-surface p-4">
                <div className="font-bold">
                  📝 {e.subjects?.name} · {formatDay(e.date)}
                </div>
                {e.topics && <div className="text-sm text-muted">{e.topics}</div>}
              </li>
            ))}
          </ul>
        </section>
      )}

      <section>
        <div className="mb-2 flex items-baseline justify-between">
          <h2 className="text-sm font-bold text-muted">Fächer</h2>
          {all.length > 0 && (
            <span className="text-sm text-muted">
              Gesamtschnitt <b className="text-foreground">{formatGrade(average(all))}</b>
            </span>
          )}
        </div>

        {list.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-border bg-surface p-8 text-center text-muted">
            Noch keine Noten. Sag dem Gehirn z. B. „Hab ne 2 in Englisch“.
          </div>
        ) : (
          <ul className="grid gap-2 sm:grid-cols-2">
            {list.map((s) => (
              <li key={s.id} className="rounded-2xl border border-border bg-surface p-4">
                <div className="flex items-baseline justify-between">
                  <span className="font-bold">{s.name}</span>
                  <span className="text-2xl font-black text-accent">
                    {formatGrade(average(s.grades))}
                  </span>
                </div>
                <div className="mt-2 flex flex-wrap gap-1">
                  {s.grades
                    .toSorted((a, b) => a.date.localeCompare(b.date))
                    .map((g, i) => (
                      <span
                        key={i}
                        title={`${g.kind} · ${g.date}`}
                        className="rounded-md bg-surface-2 px-2 py-0.5 text-sm"
                      >
                        {formatGrade(Number(g.value))}
                      </span>
                    ))}
                  {s.grades.length === 0 && <span className="text-sm text-muted">keine Noten</span>}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
