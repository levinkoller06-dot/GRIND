"use client";

import { useTransition } from "react";

export function DeleteButton({ action, label }: { action: () => Promise<void>; label: string }) {
  const [pending, start] = useTransition();
  return (
    <button
      disabled={pending}
      onClick={() => {
        if (confirm(`${label} wirklich löschen?`)) start(action);
      }}
      className="shrink-0 rounded-lg px-2 py-1 text-xs text-muted hover:bg-surface-2 hover:text-red-500 disabled:opacity-50"
      aria-label={`${label} löschen`}
    >
      {pending ? "…" : "✕"}
    </button>
  );
}
