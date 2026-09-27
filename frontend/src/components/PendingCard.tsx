"use client";

import { useState } from "react";
import { api, type EventPayload, type PendingAction } from "@/lib/api";
import { formatWhen, KIND_ICON } from "@/lib/format";

type Props = {
  action: PendingAction;
  onDone: (id: string, status: "confirmed" | "rejected") => void;
};

export function PendingCard({ action, onDone }: Props) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<EventPayload>(action.payload);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function decide(confirm: boolean) {
    setBusy(true);
    setError(null);
    try {
      if (confirm) {
        await api(`/pending/${action.id}/confirm`, {
          method: "POST",
          body: JSON.stringify({ changes: draft }),
        });
      } else {
        await api(`/pending/${action.id}/reject`, { method: "POST" });
      }
      onDone(action.id, confirm ? "confirmed" : "rejected");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Fehler");
      setBusy(false);
    }
  }

  const p = draft;
  const field = "rounded-lg border border-border bg-background px-3 py-2 text-sm";

  return (
    <div className="rounded-2xl border border-accent/40 bg-surface p-4">
      <div className="text-xs font-medium text-muted">Soll ich das eintragen?</div>

      {editing ? (
        <div className="mt-2 grid gap-2">
          <input
            className={field}
            value={draft.titel}
            onChange={(e) => setDraft({ ...draft, titel: e.target.value })}
          />
          <div className="grid grid-cols-3 gap-2">
            <input
              type="date"
              className={field}
              value={draft.datum}
              onChange={(e) => setDraft({ ...draft, datum: e.target.value })}
            />
            <input
              type="time"
              className={field}
              value={draft.uhrzeit ?? ""}
              onChange={(e) => setDraft({ ...draft, uhrzeit: e.target.value })}
              aria-label="Start"
            />
            <input
              type="time"
              className={field}
              value={draft.ende_uhrzeit ?? ""}
              onChange={(e) => setDraft({ ...draft, ende_uhrzeit: e.target.value })}
              aria-label="Ende"
            />
          </div>
        </div>
      ) : (
        <div className="mt-1">
          <div className="font-bold">
            {KIND_ICON[p.art ?? "termin"]} {p.titel}
          </div>
          <div className="text-sm text-muted">{formatWhen(p)}</div>
          {p.notiz && <div className="mt-1 text-sm text-muted">{p.notiz}</div>}
        </div>
      )}

      <div className="mt-3 flex gap-2 text-sm font-medium">
        <button
          disabled={busy}
          onClick={() => decide(true)}
          className="rounded-lg bg-accent px-3 py-1.5 text-accent-fg disabled:opacity-60"
        >
          ✓ Eintragen
        </button>
        <button
          disabled={busy}
          onClick={() => setEditing(!editing)}
          className="rounded-lg border border-border px-3 py-1.5 hover:bg-surface-2"
        >
          ✎ {editing ? "Fertig" : "Ändern"}
        </button>
        <button
          disabled={busy}
          onClick={() => decide(false)}
          className="rounded-lg border border-border px-3 py-1.5 text-muted hover:bg-surface-2"
        >
          ✕ Nein
        </button>
      </div>
      {error && <p className="mt-2 text-sm text-red-500">{error}</p>}
    </div>
  );
}
