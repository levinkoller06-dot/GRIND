"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Suggestion = { uhrzeit: string; essen: string; kcal: number; protein_g: number; grund?: string };
type Result = { vorschlaege: Suggestion[]; hinweis?: string };
type State = { fingerprint: string; result?: Result; error?: string };

const STORAGE_KEY = "grind.mealSuggestions";

function loadCached(fingerprint: string): Result | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const cached = raw ? JSON.parse(raw) : null;
    return cached?.fingerprint === fingerprint ? cached.result : null;
  } catch {
    return null;
  }
}

function saveCached(fingerprint: string, result: Result) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ fingerprint, result }));
  } catch {
    // Speicher nicht verfügbar (z. B. privates Fenster) – dann eben ohne Cache
  }
}

/** Gespeicherte Vorschläge, sonst vom Backend (und dann speichern). */
async function fetchSuggestions(fingerprint: string, force: boolean): Promise<Result> {
  const cached = force ? null : loadCached(fingerprint);
  if (cached) return cached;
  const fresh = await api<Result>(`/nutrition/suggestions${force ? "?force=true" : ""}`);
  saveCached(fingerprint, fresh);
  return fresh;
}

/**
 * `fingerprint` ändert sich nur, wenn heute etwas gegessen wurde oder die Ziele geändert
 * wurden. Solange er gleich bleibt, werden die gespeicherten Vorschläge gezeigt.
 */
export function MealSuggestions({ fingerprint }: { fingerprint: string }) {
  const [state, setState] = useState<State | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    let active = true;
    fetchSuggestions(fingerprint, false)
      .then((result) => active && setState({ fingerprint, result }))
      .catch((e) => active && setState({ fingerprint, error: e.message }));
    return () => {
      active = false;
    };
  }, [fingerprint]);

  async function refresh() {
    setRefreshing(true);
    try {
      setState({ fingerprint, result: await fetchSuggestions(fingerprint, true) });
    } catch (e) {
      setState({ fingerprint, error: e instanceof Error ? e.message : "Fehler" });
    } finally {
      setRefreshing(false);
    }
  }

  const current = state?.fingerprint === fingerprint ? state : null;
  const result = current?.result;

  return (
    <section className="flex flex-col rounded-2xl border border-border bg-surface p-4 md:min-h-0">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h2 className="font-bold">💡 Vorschläge für heute</h2>
          <p className="mb-3 text-xs text-muted">Damit du deine Ziele noch erreichst</p>
        </div>
        <button
          onClick={refresh}
          disabled={refreshing || !current}
          className="shrink-0 rounded-lg border border-border px-2.5 py-1 text-xs hover:bg-surface-2 disabled:opacity-50"
        >
          🔄 Andere Vorschläge
        </button>
      </div>

      {!current && <p className="text-sm text-muted">Gehirn plant …</p>}
      {current?.error && <p className="text-sm text-red-500">{current.error}</p>}

      {result && (
        <div className={`space-y-2 md:min-h-0 md:overflow-y-auto ${refreshing ? "opacity-50" : ""}`}>
          {result.vorschlaege.map((s, i) => (
            <div key={i} className="flex gap-3 rounded-xl bg-surface-2 p-3">
              <div className="w-12 shrink-0 font-mono text-sm font-bold text-accent">{s.uhrzeit}</div>
              <div className="min-w-0 flex-1">
                <div className="font-medium">{s.essen}</div>
                <div className="text-xs text-muted">
                  ca. {Math.round(s.kcal)} kcal · {Math.round(s.protein_g)} g Protein
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
