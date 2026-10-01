"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

type Status = {
  verbunden: boolean;
  zuletzt?: string | null;
  neu?: number;
  geaendert?: number;
  entfernt?: number;
};

const since = (iso: string) =>
  new Date(iso).toLocaleString("de-DE", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });

export function MoodleConnect() {
  const router = useRouter();
  const [status, setStatus] = useState<Status | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  useEffect(() => {
    api<Status>("/moodle")
      .then(setStatus)
      .catch((e) => setError(e.message));
  }, []);

  async function run(action: () => Promise<Status>) {
    setBusy(true);
    setError(null);
    setInfo(null);
    try {
      const result = await action();
      setStatus(result);
      if (result.neu !== undefined) {
        setInfo(`${result.neu} neu, ${result.geaendert ?? 0} geändert, ${result.entfernt ?? 0} entfernt`);
      }
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Fehler");
    } finally {
      setBusy(false);
    }
  }

  function connect(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const url = String(new FormData(event.currentTarget).get("url") ?? "").trim();
    run(() => api<Status>("/moodle", { method: "PUT", body: JSON.stringify({ url }) }));
  }

  function disconnect() {
    if (!confirm("Moodle trennen? Die importierten Abgaben und Prüfungen werden aus dem Kalender entfernt.")) return;
    run(() => api<Status>("/moodle", { method: "DELETE" }));
  }

  const button = "rounded-lg border border-border px-3 py-1 text-sm hover:bg-surface-2 disabled:opacity-50";

  return (
    <section className="space-y-3 rounded-2xl border border-border bg-surface p-4">
      <h2 className="font-bold">📚 Moodle (Berufsschule)</h2>
      {status?.verbunden ? (
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-sm text-muted">
            Verbunden{status.zuletzt ? ` · zuletzt abgeglichen ${since(status.zuletzt)}` : ""}
          </p>
          <div className="flex gap-2">
            <button disabled={busy} onClick={() => run(() => api<Status>("/moodle/sync?force=true", { method: "POST" }))} className={button}>
              {busy ? "…" : "Jetzt abgleichen"}
            </button>
            <button disabled={busy} onClick={disconnect} className={button}>
              Trennen
            </button>
          </div>
        </div>
      ) : (
        status && (
          <form onSubmit={connect} className="space-y-2">
            <p className="text-sm text-muted">
              Moodle → Kalender → <b>Kalender exportieren</b> → „Alle Termine“ und „Letzte und nächste 60 Tage“ →{" "}
              <b>Kalender-URL abrufen</b>. Den Link hier einfügen – Abgaben und Prüfungen kommen dann automatisch in
              den Kalender.
            </p>
            <input
              name="url"
              type="url"
              required
              placeholder="https://moodle.bzu.ch/calendar/export_execute.php?…"
              className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm"
            />
            <button disabled={busy} className="rounded-xl bg-accent px-4 py-2 text-sm font-semibold text-accent-fg disabled:opacity-50">
              {busy ? "Verbinde …" : "Verbinden"}
            </button>
          </form>
        )
      )}
      {info && <p className="text-sm text-muted">{info}</p>}
      {error && <p className="text-sm text-red-500">{error}</p>}
    </section>
  );
}
