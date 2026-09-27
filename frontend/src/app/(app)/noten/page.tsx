import { PageHeader } from "@/components/PageHeader";
import { TABS } from "@/components/tabs";
import { createClient } from "@/lib/supabase/server";
import { formatDay, todayIso } from "@/lib/format";
import { average, formatGrade, gradeColor, type Grade, type GradeScale } from "@/lib/grades";

const tab = TABS.find((t) => t.href === "/noten")!;

type Subject = { id: string; name: string; aliases: string[]; grades: Grade[] };
type Exam = { id: string; date: string; topics: string | null; subjects: { name: string } | null };

export default async function NotenPage() {
  const supabase = await createClient();
  const { data: claims } = await supabase.auth.getClaims();

  const [{ data: subjects }, { data: exams }, { data: profile }] = await Promise.all([
    supabase.from("subjects").select("id,name,aliases,grades(value,weight,kind,date)").order("name"),
    supabase.from("exams").select("id,date,topics,subjects(name)").gte("date", todayIso()).order("date"),
    supabase.from("profiles").select("grade_scale").eq("id", claims?.claims?.sub ?? "").maybeSingle(),
  ]);

  const scale = (profile?.grade_scale ?? "ch") as GradeScale;
  const list = (subjects ?? []) as Subject[];
  const upcoming = (exams ?? []) as unknown as Exam[];
  const all = list.flatMap((s) => s.grades);

  return (
    <div className="flex flex-col md:min-h-0 md:flex-1">
      <PageHeader tab={tab}>
        {all.length > 0 && (
          <div className="rounded-xl border border-border bg-surface px-3 py-1.5 text-sm">
            Gesamtschnitt{" "}
            <b className={`text-lg ${gradeColor(average(all), scale)}`}>{formatGrade(average(all))}</b>
          </div>
        )}
      </PageHeader>

      {upcoming.length > 0 && (
        <section className="mb-4 flex flex-wrap gap-2">
          {upcoming.map((e) => (
            <div
              key={e.id}
              title={e.topics ?? undefined}
              className="rounded-xl border border-red-500/40 bg-red-500/10 px-3 py-1.5 text-sm"
            >
              📝 <b>{e.subjects?.name}</b> · {formatDay(e.date)}
              {e.topics && <span className="text-muted"> · {e.topics}</span>}
            </div>
          ))}
        </section>
      )}

      {list.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-border bg-surface p-8 text-center text-muted">
          Noch keine Fächer. Sag dem Gehirn z. B. „Leg die Fächer Mathe, Englisch und Sport an“.
        </div>
      ) : (
        <ul className="grid auto-rows-min grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {list.map((s) => {
            const avg = average(s.grades);
            return (
              <li key={s.id} className="flex flex-col rounded-2xl border border-border bg-surface p-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="truncate font-bold">{s.name}</div>
                    {s.aliases.length > 0 && (
                      <div className="truncate text-[11px] text-muted">{s.aliases.join(" · ")}</div>
                    )}
                  </div>
                  <div className="text-right">
                    <div className={`text-2xl font-black leading-none ${gradeColor(avg, scale)}`}>
                      {formatGrade(avg)}
                    </div>
                    <div className="text-[10px] text-muted">Schnitt</div>
                  </div>
                </div>
                <div className="mt-2 flex flex-wrap gap-1">
                  {s.grades
                    .toSorted((a, b) => a.date.localeCompare(b.date))
                    .map((g, i) => (
                      <span
                        key={i}
                        title={`${g.kind} · ${formatDay(g.date)}`}
                        className={`rounded-md bg-surface-2 px-1.5 py-0.5 text-xs font-semibold ${gradeColor(Number(g.value), scale)}`}
                      >
                        {formatGrade(Number(g.value))}
                      </span>
                    ))}
                  {s.grades.length === 0 && <span className="text-xs text-muted">noch keine Noten</span>}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
