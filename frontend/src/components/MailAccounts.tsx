"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Account = { id: string; email: string; label: string | null; imap_host: string };

const PRESETS = {
  hispeed: { label: "hispeed / Sunrise", hint: "Dein normales hispeed-Passwort." },
  gmail: {
    label: "Gmail",
    hint: "Braucht ein App-Passwort: Google-Konto → Sicherheit → Bestätigung in zwei Schritten aktivieren → App-Passwörter (myaccount.google.com/apppasswords).",
  },
  gmx: { label: "GMX", hint: "In den GMX-Einstellungen IMAP/POP3 erlauben." },
  andere: { label: "Anderer Anbieter", hint: "IMAP- und SMTP-Server beim Anbieter nachschauen." },
} as const;

type Preset = keyof typeof PRESETS;

export function MailAccounts() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [adding, setAdding] = useState(false);
  const [preset, setPreset] = useState<Preset>("hispeed");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<Account[]>("/mail/accounts")
      .then(setAccounts)
      .catch((e) => setError(e.message));
  }, []);

  async function add(form: FormData) {
    setBusy(true);
    setError(null);
    const value = (k: string) => String(form.get(k) ?? "").trim() || null;
    const port = (k: string) => (value(k) ? Number(value(k)) : null);
    try {
      const account = await api<Account>("/mail/accounts", {
        method: "POST",
        body: JSON.stringify({
          email: value("email"),
          password: String(form.get("password") ?? ""),
          label: value("label"),
          preset: preset === "andere" ? null : preset,
          imap_host: value("imap_host"),
          imap_port: port("imap_port"),
          smtp_host: value("smtp_host"),
          smtp_port: port("smtp_port"),
        }),
      });
      setAccounts((a) => [...a, account]);
      setAdding(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Fehler");
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    if (!confirm("Mail-Konto trennen?")) return;
    await api(`/mail/accounts/${id}`, { method: "DELETE" });
    setAccounts((a) => a.filter((x) => x.id !== id));
  }

  const field = "w-full rounded-xl border border-border bg-background px-3 py-2 text-sm";

  return (
    <section className="space-y-3 rounded-2xl border border-border bg-surface p-4">
      <div className="flex items-center justify-between">
        <h2 className="font-bold">📬 Mail-Konten</h2>
        {!adding && (
          <button onClick={() => setAdding(true)} className="rounded-lg border border-border px-3 py-1 text-sm hover:bg-surface-2">
            + Hinzufügen
          </button>
        )}
      </div>

      {accounts.length === 0 && !adding && <p className="text-sm text-muted">Noch keine Mail-Konten verbunden.</p>}
      <ul className="divide-y divide-border">
        {accounts.map((a) => (
          <li key={a.id} className="flex items-center justify-between py-2 text-sm">
            <span>
              <b>{a.label ?? a.email}</b>
              {a.label && <span className="text-muted"> · {a.email}</span>}
            </span>
            <button onClick={() => remove(a.id)} className="text-xs text-muted hover:text-red-500">
              Trennen
            </button>
          </li>
        ))}
      </ul>

      {adding && (
        <form action={add} className="space-y-2 rounded-xl bg-surface-2 p-3">
          <select value={preset} onChange={(e) => setPreset(e.target.value as Preset)} className={field}>
            {(Object.keys(PRESETS) as Preset[]).map((p) => (
              <option key={p} value={p}>
                {PRESETS[p].label}
              </option>
            ))}
          </select>
          <p className="text-xs text-muted">{PRESETS[preset].hint}</p>
          <input name="email" type="email" required placeholder="E-Mail-Adresse" className={field} autoComplete="off" />
          <input name="password" type="password" required placeholder="Passwort / App-Passwort" className={field} autoComplete="new-password" />
          <input name="label" placeholder="Name (optional), z. B. Privat" className={field} />
          {preset === "andere" && (
            <div className="grid grid-cols-[1fr_5rem] gap-2">
              <input name="imap_host" required placeholder="IMAP-Server" className={field} />
              <input name="imap_port" required placeholder="993" defaultValue="993" className={field} />
              <input name="smtp_host" required placeholder="SMTP-Server" className={field} />
              <input name="smtp_port" required placeholder="587" defaultValue="587" className={field} />
            </div>
          )}
          <div className="flex gap-2">
            <button disabled={busy} className="rounded-lg bg-accent px-3 py-1.5 text-sm font-bold text-accent-fg disabled:opacity-60">
              {busy ? "Prüfe Anmeldung …" : "Verbinden"}
            </button>
            <button type="button" onClick={() => setAdding(false)} className="rounded-lg border border-border px-3 py-1.5 text-sm">
              Abbrechen
            </button>
          </div>
          <p className="text-[11px] text-muted">Das Passwort wird verschlüsselt gespeichert und nur für den Mail-Abruf benutzt.</p>
        </form>
      )}

      {error && <p className="text-sm text-red-500">{error}</p>}
      <p className="text-xs text-muted">Schul-Mail (Microsoft 365) kommt im nächsten Schritt über den Microsoft-Login.</p>
    </section>
  );
}
