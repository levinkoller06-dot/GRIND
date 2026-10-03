"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Meldung = {
  id: string;
  kind: "morgen" | "erinnerung" | "mail";
  title: string;
  body: string | null;
  link: string | null;
  created_at: string;
};

const POLL_MS = 60_000;

const ago = (iso: string) =>
  new Date(iso).toLocaleString("de-DE", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });

/** Meldungen aus dem Zeitplan (Morgen-Check, Erinnerungen, neue Mails) im Gehirn-Tab. */
export function Notifications() {
  const [items, setItems] = useState<Meldung[]>([]);

  useEffect(() => {
    const load = () =>
      api<{ meldungen: Meldung[] }>("/notifications")
        .then((r) => setItems(r.meldungen))
        .catch(() => {}); // Migration fehlt oder Backend aus: Karte einfach nicht zeigen
    load();
    const id = setInterval(load, POLL_MS);
    return () => clearInterval(id);
  }, []);

  function dismiss(id: string) {
    setItems((list) => list.filter((m) => m.id !== id));
    api(`/notifications/${id}/read`, { method: "POST" }).catch(() => {});
  }

  function dismissAll() {
    setItems([]);
    api("/notifications/read-all", { method: "POST" }).catch(() => {});
  }

  if (!items.length) return null;

  return (
    <section className="space-y-2">
      {items.length > 1 && (
        <div className="flex justify-end">
          <button onClick={dismissAll} className="text-xs text-muted hover:text-foreground">
            Alle als gelesen markieren
          </button>
        </div>
      )}
      {items.map((m) => (
        <div
          key={m.id}
          className={`flex gap-3 rounded-2xl border bg-surface p-4 ${
            m.kind === "erinnerung" ? "border-accent/60" : "border-border"
          }`}
        >
          <div className="min-w-0 flex-1">
            <div className="flex items-baseline justify-between gap-2">
              {m.link ? (
                <Link href={m.link} onClick={() => dismiss(m.id)} className="font-bold hover:underline">
                  {m.title}
                </Link>
              ) : (
                <span className="font-bold">{m.title}</span>
              )}
              <span className="shrink-0 text-xs text-muted">{ago(m.created_at)}</span>
            </div>
            {m.body && <p className="mt-1 whitespace-pre-line text-sm text-muted">{m.body}</p>}
          </div>
          <button
            onClick={() => dismiss(m.id)}
            aria-label="Gelesen"
            className="h-7 w-7 shrink-0 rounded-lg border border-border text-sm text-muted hover:bg-surface-2"
          >
            ✓
          </button>
        </div>
      ))}
    </section>
  );
}
