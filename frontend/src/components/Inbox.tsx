"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { TZ } from "@/lib/format";

type Mail = {
  id: string;
  konto: string;
  konto_label: string | null;
  von: { name: string; email: string };
  betreff: string;
  datum: string | null;
  gelesen: boolean;
  newsletter: boolean;
  vorschau: string;
};

type Inbox = { mails: Mail[]; fehler: { konto: string; fehler: string }[]; konten: string[] };
type FullMail = Mail & { text: string; an: string };

const COLORS = ["bg-sky-500", "bg-violet-500", "bg-amber-500", "bg-rose-500", "bg-emerald-500"];

function when(iso: string | null) {
  if (!iso) return "";
  const d = new Date(iso);
  const today = new Date().toLocaleDateString("sv-SE", { timeZone: TZ });
  return d.toLocaleDateString("sv-SE", { timeZone: TZ }) === today
    ? d.toLocaleTimeString("de-DE", { timeZone: TZ, hour: "2-digit", minute: "2-digit" })
    : d.toLocaleDateString("de-DE", { timeZone: TZ, day: "2-digit", month: "2-digit" });
}

export function Inbox() {
  const [inbox, setInbox] = useState<Inbox | null>(null);
  const [open, setOpen] = useState<FullMail | null>(null);
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<Inbox>("/mail/inbox")
      .then(setInbox)
      .catch((e) => setError(e.message));
  }, []);

  async function show(mail: Mail) {
    setLoadingId(mail.id);
    try {
      setOpen(await api<FullMail>(`/mail/message/${encodeURIComponent(mail.id)}`));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Fehler");
    } finally {
      setLoadingId(null);
    }
  }

  async function trash(mail: FullMail) {
    if (!confirm(`„${mail.betreff}“ in den Papierkorb verschieben?`)) return;
    try {
      await api(`/mail/message/${encodeURIComponent(mail.id)}`, { method: "DELETE" });
      setInbox((box) => box && { ...box, mails: box.mails.filter((m) => m.id !== mail.id) });
      setOpen(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Fehler");
    }
  }

  const color = (konto: string) => COLORS[Math.max(0, inbox?.konten.indexOf(konto) ?? 0) % COLORS.length];

  if (error && !inbox) return <p className="text-sm text-red-500">{error}</p>;
  if (!inbox) return <p className="text-sm text-muted">Hole Mails aus allen Postfächern …</p>;
  if (inbox.konten.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-border bg-surface p-8 text-center text-muted">
        Noch kein Mail-Konto verbunden.{" "}
        <Link href="/einstellungen" className="text-accent underline">
          In den Einstellungen hinzufügen
        </Link>
      </div>
    );
  }

  return (
    <div className="grid gap-4 md:min-h-0 md:flex-1 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
      <section className="flex flex-col rounded-2xl border border-border bg-surface md:min-h-0">
        <div className="flex flex-wrap gap-2 border-b border-border p-3 text-xs">
          {inbox.konten.map((k) => (
            <span key={k} className="flex items-center gap-1">
              <span className={`size-2 rounded-full ${color(k)}`} /> {k}
            </span>
          ))}
        </div>
        {inbox.fehler.map((f) => (
          <p key={f.konto} className="border-b border-border px-3 py-2 text-xs text-red-500">
            {f.konto}: {f.fehler}
          </p>
        ))}
        <ul className="divide-y divide-border md:min-h-0 md:overflow-y-auto">
          {inbox.mails.length === 0 && <li className="p-4 text-sm text-muted">Keine Mails in den letzten 7 Tagen.</li>}
          {inbox.mails.map((m) => (
            <li key={m.id}>
              <button
                onClick={() => show(m)}
                className={`flex w-full gap-2 px-3 py-2 text-left hover:bg-surface-2 ${open?.id === m.id ? "bg-surface-2" : ""}`}
              >
                <span className={`mt-1.5 size-2 shrink-0 rounded-full ${color(m.konto)}`} title={m.konto} />
                <span className="min-w-0 flex-1">
                  <span className="flex justify-between gap-2 text-sm">
                    <span className={`truncate ${m.gelesen ? "" : "font-bold"}`}>{m.von.name}</span>
                    <span className="shrink-0 text-xs text-muted">{loadingId === m.id ? "…" : when(m.datum)}</span>
                  </span>
                  <span className={`block truncate text-sm ${m.gelesen ? "text-muted" : ""}`}>
                    {m.newsletter && (
                      <span className="mr-1 rounded bg-surface-2 px-1 text-[10px] text-muted">Newsletter</span>
                    )}
                    {m.betreff}
                  </span>
                  <span className="block truncate text-xs text-muted">{m.vorschau}</span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      </section>

      <section className="flex flex-col rounded-2xl border border-border bg-surface p-4 md:min-h-0">
        {open ? (
          <>
            <div className="flex items-start justify-between gap-2">
              <h2 className="text-lg font-bold">{open.betreff}</h2>
              <button
                onClick={() => trash(open)}
                className="shrink-0 rounded-lg border border-border px-2.5 py-1 text-xs hover:border-red-500 hover:text-red-500"
              >
                🗑 Löschen
              </button>
            </div>
            <p className="text-sm text-muted">
              {open.von.name} &lt;{open.von.email}&gt; → {open.konto} · {when(open.datum)}
            </p>
            <div className="selectable mt-3 whitespace-pre-wrap text-sm md:min-h-0 md:flex-1 md:overflow-y-auto">
              {open.text || "(kein Text)"}
            </div>
            <p className="mt-3 text-xs text-muted">
              Antworten? Sag dem Gehirn z. B. „Antworte {open.von.name.split(" ")[0]}, dass …“ · Aufräumen:
              „Lösch alle Werbemails“
            </p>
          </>
        ) : (
          <p className="m-auto text-sm text-muted">Mail anklicken zum Lesen</p>
        )}
      </section>
    </div>
  );
}
