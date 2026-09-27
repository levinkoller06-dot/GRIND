"use client";

import { useState } from "react";
import { api, type PendingAction } from "@/lib/api";

type Payload = {
  anzahl: number;
  grund?: string;
  vorschau: { von: string; betreff: string }[];
};

type Props = {
  action: PendingAction;
  onDone: (id: string, status: "confirmed" | "rejected") => void;
};

export function MailDeleteCard({ action, onDone }: Props) {
  const p = action.payload as unknown as Payload;
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function decide(confirm: boolean) {
    setBusy(true);
    setError(null);
    try {
      await api(`/pending/${action.id}/${confirm ? "confirm" : "reject"}`, {
        method: "POST",
        body: JSON.stringify({ changes: {} }),
      });
      onDone(action.id, confirm ? "confirmed" : "rejected");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Fehler");
      setBusy(false);
    }
  }

  return (
    <div className="rounded-2xl border border-red-500/50 bg-surface p-4">
      <div className="text-xs font-medium text-muted">Soll ich diese Mails in den Papierkorb verschieben?</div>
      <div className="mt-1 font-bold">
        🗑 {p.anzahl} Mail{p.anzahl === 1 ? "" : "s"}
        {p.grund && <span className="font-normal text-muted"> · {p.grund}</span>}
      </div>
      <ul className="mt-2 max-h-40 space-y-0.5 overflow-y-auto rounded-lg bg-surface-2 p-2 text-xs">
        {p.vorschau.map((m, i) => (
          <li key={i} className="truncate">
            <b>{m.von}</b> <span className="text-muted">· {m.betreff}</span>
          </li>
        ))}
      </ul>
      <div className="mt-3 flex gap-2 text-sm font-medium">
        <button
          disabled={busy}
          onClick={() => decide(true)}
          className="rounded-lg bg-red-500 px-3 py-1.5 text-white disabled:opacity-60"
        >
          {busy ? "Verschiebe …" : "🗑 In den Papierkorb"}
        </button>
        <button
          disabled={busy}
          onClick={() => decide(false)}
          className="rounded-lg border border-border px-3 py-1.5 text-muted hover:bg-surface-2"
        >
          ✕ Behalten
        </button>
      </div>
      <p className="mt-2 text-[11px] text-muted">Im Papierkorb deines Postfachs kannst du sie wiederherstellen.</p>
      {error && <p className="mt-2 text-sm text-red-500">{error}</p>}
    </div>
  );
}
