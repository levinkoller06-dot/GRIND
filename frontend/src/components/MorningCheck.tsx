"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { saveMorningCheck } from "@/app/(app)/einstellungen/actions";

type Props = {
  /** "HH:MM:SS" aus der Datenbank, null = aus, undefined = Migration fehlt */
  time: string | null | undefined;
};

/** Einstellungen für den Zeitplan: Uhrzeit des Morgen-Checks + Knopf zum Ausprobieren. */
export function MorningCheck({ time }: Props) {
  const [active, setActive] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);
  const [info, setInfo] = useState<string | null>(null);

  useEffect(() => {
    api<{ zeitplan_aktiv: boolean }>("/notifications")
      .then((r) => setActive(r.zeitplan_aktiv))
      .catch(() => setActive(null));
  }, []);

  async function test() {
    setBusy(true);
    setInfo(null);
    try {
      await api("/jobs/morning-check", { method: "POST" });
      setInfo("Erledigt – schau im Gehirn-Tab nach.");
    } catch (e) {
      setInfo(e instanceof Error ? e.message : "Fehler");
    } finally {
      setBusy(false);
    }
  }

  const field = "rounded-xl border border-border bg-background px-3 py-2 text-sm";

  return (
    <section className="space-y-3 rounded-2xl border border-border bg-surface p-4">
      <h2 className="font-bold">⏰ Morgen-Check & Erinnerungen</h2>
      <p className="text-sm text-muted">
        Jeden Morgen eine Übersicht mit Terminen, Tests, Training und Erinnerungen. Dazu ruft GRIND
        im Hintergrund deine Mails ab und meldet neue im Gehirn-Tab.
      </p>
      {time === undefined ? (
        <p className="text-sm text-red-500">
          Datenbank ist nicht aktuell: bitte die neue SQL-Datei aus supabase/migrations ausführen.
        </p>
      ) : (
        <form action={saveMorningCheck} className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" name="morning_on" defaultChecked={time !== null} />
            Morgen-Check um
          </label>
          <input
            type="time"
            name="morning_check_time"
            defaultValue={(time ?? "06:30").slice(0, 5)}
            className={field}
          />
          <button className="rounded-xl bg-accent px-4 py-2 text-sm font-bold text-accent-fg">Speichern</button>
          <button
            type="button"
            disabled={busy}
            onClick={test}
            className="rounded-xl border border-border px-4 py-2 text-sm hover:bg-surface-2 disabled:opacity-50"
          >
            {busy ? "…" : "Jetzt testen"}
          </button>
        </form>
      )}
      {info && <p className="text-sm text-muted">{info}</p>}
      {active === false && (
        <p className="text-sm text-muted">
          ⚠️ Der Zeitplan ist im Backend noch aus: <code>SUPABASE_SECRET_KEY</code> in{" "}
          <code>backend/.env</code> eintragen und das Backend neu starten.
        </p>
      )}
    </section>
  );
}
