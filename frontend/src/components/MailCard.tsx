"use client";

import { useState } from "react";
import { api, type PendingAction } from "@/lib/api";

export type MailPayload = { von: string; an: string; betreff: string; text: string };

type Props = {
  action: PendingAction;
  onDone: (id: string, status: "confirmed" | "rejected") => void;
};

export function MailCard({ action, onDone }: Props) {
  const initial = action.payload as unknown as MailPayload;
  const [draft, setDraft] = useState<MailPayload>(initial);
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function decide(confirm: boolean) {
    setBusy(true);
    setError(null);
    try {
      if (confirm) {
        await api(`/pending/${action.id}/confirm`, {
          method: "POST",
          body: JSON.stringify({ changes: { an: draft.an, betreff: draft.betreff, text: draft.text } }),
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

  const field = "w-full rounded-lg border border-border bg-background px-3 py-2 text-sm";

  return (
    <div className="rounded-2xl border border-sky-500/50 bg-surface p-4">
      <div className="text-xs font-medium text-muted">Soll ich diese Mail senden?</div>
      <div className="mt-1 text-xs text-muted">
        Von <b className="text-foreground">{draft.von}</b>
      </div>

      {editing ? (
        <div className="mt-2 grid gap-2">
          <input className={field} value={draft.an} onChange={(e) => setDraft({ ...draft, an: e.target.value })} />
          <input
            className={field}
            value={draft.betreff}
            onChange={(e) => setDraft({ ...draft, betreff: e.target.value })}
          />
          <textarea
            className={`${field} min-h-40`}
            value={draft.text}
            onChange={(e) => setDraft({ ...draft, text: e.target.value })}
          />
        </div>
      ) : (
        <>
          <div className="text-xs text-muted">
            An <b className="text-foreground">{draft.an}</b>
          </div>
          <div className="mt-1 font-bold">{draft.betreff}</div>
          <div className="selectable mt-2 max-h-48 overflow-y-auto whitespace-pre-wrap rounded-lg bg-surface-2 p-3 text-sm">
            {draft.text}
          </div>
        </>
      )}

      <div className="mt-3 flex gap-2 text-sm font-medium">
        <button
          disabled={busy}
          onClick={() => decide(true)}
          className="rounded-lg bg-sky-500 px-3 py-1.5 text-white disabled:opacity-60"
        >
          {busy ? "Sende …" : "✉️ Senden"}
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
