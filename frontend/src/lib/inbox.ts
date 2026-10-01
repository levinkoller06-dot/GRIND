import { api } from "@/lib/api";

export type Mail = {
  id: string;
  konto: string;
  konto_label: string | null;
  von: { name: string; email: string };
  betreff: string;
  datum: string | null;
  gelesen: boolean;
  newsletter: boolean;
  kategorie: string | null;
  antwort_noetig: boolean;
  vorschau: string;
};

export type Inbox = {
  mails: Mail[];
  fehler: { konto: string; fehler: string }[];
  konten: string[];
  aussortiert: number;
};

// Das Postfach wird schon beim Start der App geladen (siehe StartupSync), damit der
// Mails-Tab sofort etwas zeigt. Werbung räumt das Backend dabei gleich weg.
let cached: Inbox | null = null;
let loading: Promise<Inbox> | null = null;
/** Seit dem Start der App automatisch in den Papierkorb verschobene Werbung */
let sortedOut = 0;

export function cachedInbox() {
  return cached && { ...cached, aussortiert: sortedOut };
}

export function loadInbox(): Promise<Inbox> {
  loading ??= api<Inbox>("/mail/inbox")
    .then((box) => {
      sortedOut += box.aussortiert ?? 0;
      cached = box;
      return { ...box, aussortiert: sortedOut };
    })
    .finally(() => {
      loading = null;
    });
  return loading;
}

export function forgetMail(id: string) {
  if (cached) cached = { ...cached, mails: cached.mails.filter((m) => m.id !== id) };
}
