"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Suggestion = { uhrzeit: string; essen: string; kcal: number; protein_g: number; grund?: string };
type Result = { vorschlaege: Suggestion[]; hinweis?: string };

export function MealSuggestions() {
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<Result>("/nutrition/suggestions")
      .then(setResult)
      .catch((e) => setError(e.message));
  }, []);

  return (
    <section className="flex flex-col rounded-2xl border border-border bg-surface p-4 md:min-h-0">
      <h2 className="font-bold">💡 Vorschläge für heute</h2>
      <p className="mb-3 text-xs text-muted">Damit du deine Ziele noch erreichst</p>

      {!result && !error && <p className="text-sm text-muted">Gehirn plant …</p>}
      {error && <p className="text-sm text-red-500">{error}</p>}

      {result && (
        <div className="space-y-2 md:min-h-0 md:overflow-y-auto">
          {result.vorschlaege.map((s, i) => (
            <div key={i} className="flex gap-3 rounded-xl bg-surface-2 p-3">
              <div className="w-12 shrink-0 font-mono text-sm font-bold text-accent">{s.uhrzeit}</div>
              <div className="min-w-0 flex-1">
                <div className="font-medium">{s.essen}</div>
                <div className="text-xs text-muted">
                  {Math.round(s.kcal)} kcal · {Math.round(s.protein_g)} g Protein
                  {s.grund && ` · ${s.grund}`}
                </div>
              </div>
            </div>
          ))}
          {result.hinweis && <p className="text-sm text-muted">{result.hinweis}</p>}
        </div>
      )}
    </section>
  );
}
