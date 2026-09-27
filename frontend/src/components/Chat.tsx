"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api, type ChatMessage, type ChatResponse, type PendingAction } from "@/lib/api";
import { prepareImage, type ChatImage } from "@/lib/image";
import { MailCard } from "./MailCard";
import { MailDeleteCard } from "./MailDeleteCard";
import { PendingCard } from "./PendingCard";

const EXAMPLES = [
  "Donnerstag ist Mathetest über Brüche",
  "Hab 3×10 Liegestütze gemacht",
  "Mittag gab's Nudeln mit Hähnchen",
  "Wie viel Protein hatte ich heute?",
];

/** Zeigt **fett** aus KI-Antworten als fetten Text an. */
function RichText({ text }: { text: string }) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith("**") && part.endsWith("**") ? (
      <strong key={i}>{part.slice(2, -2)}</strong>
    ) : (
      part
    ),
  );
}

export function Chat() {
  const router = useRouter();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [pending, setPending] = useState<PendingAction[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [image, setImage] = useState<ChatImage | null>(null);
  const bottom = useRef<HTMLDivElement>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  // Sofort wirksame Sperre (useState wäre bei schnellem Doppel-Enter zu spät)
  const sending = useRef(false);

  async function pickImage(file: File | undefined) {
    if (!file) return;
    try {
      setImage(await prepareImage(file));
    } catch {
      setError("Foto konnte nicht gelesen werden");
    }
  }

  useEffect(() => {
    Promise.all([api<ChatMessage[]>("/chat/history"), api<PendingAction[]>("/pending")])
      .then(([history, open]) => {
        setMessages(history);
        setPending(open);
      })
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [messages, pending, busy]);

  async function send(text: string) {
    const photo = image;
    const message = text.trim() || (photo ? "Was hab ich hier gegessen? Trag es ein." : "");
    if (!message || sending.current) return;
    sending.current = true;
    setInput("");
    setImage(null);
    setError(null);
    setBusy(true);
    setMessages((m) => [...m, { role: "user", content: message, image: photo?.preview }]);
    try {
      const res = await api<ChatResponse>("/chat", {
        method: "POST",
        body: JSON.stringify({
          message,
          image: photo ? { mime_type: photo.mime_type, data: photo.data } : null,
        }),
      });
      setMessages((m) => [...m, { role: "assistant", content: res.reply }]);
      setPending((p) => [...p, ...res.pending]);
      if (res.tools.length) router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Fehler");
    } finally {
      sending.current = false;
      setBusy(false);
    }
  }

  function onDecided(id: string) {
    setPending((p) => p.filter((a) => a.id !== id));
    router.refresh();
  }

  return (
    <section className="flex h-[70dvh] flex-col rounded-2xl border border-border bg-surface p-4 md:h-full md:min-h-0">
      <h2 className="mb-3 font-bold">🧠 Gehirn</h2>

      <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto pr-1">
        {messages.length === 0 && !busy && (
          <div className="rounded-xl bg-surface-2 p-3 text-sm text-muted">
            Schreib einfach, was ansteht. Ich sortiere es für dich ein.
          </div>
        )}
        {messages.map((m, i) => (
          <div
            key={m.id ?? `local-${i}`}
            className={`selectable max-w-[85%] whitespace-pre-wrap rounded-2xl px-3 py-2 text-sm ${
              m.role === "user"
                ? "self-end rounded-br-sm bg-accent text-accent-fg"
                : "self-start rounded-bl-sm bg-surface-2"
            }`}
          >
            {m.image && (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={m.image} alt="" className="mb-1 max-h-48 rounded-lg" />
            )}
            {m.role === "assistant" ? <RichText text={m.content} /> : m.content}
          </div>
        ))}
        {busy && (
          <div className="self-start rounded-2xl rounded-bl-sm bg-surface-2 px-3 py-2 text-sm text-muted">
            denkt nach …
          </div>
        )}
        {pending.map((a) =>
          a.kind === "mail.send" ? (
            <MailCard key={a.id} action={a} onDone={onDecided} />
          ) : a.kind === "mail.delete" ? (
            <MailDeleteCard key={a.id} action={a} onDone={onDecided} />
          ) : (
            <PendingCard key={a.id} action={a} onDone={onDecided} />
          ),
        )}
        <div ref={bottom} />
      </div>

      {error && <p className="mt-2 text-sm text-red-500">{error}</p>}

      {messages.length === 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              onClick={() => send(ex)}
              className="rounded-full border border-border px-3 py-1 text-xs text-muted hover:bg-surface-2"
            >
              {ex}
            </button>
          ))}
        </div>
      )}

      {image && (
        <div className="mt-3 flex items-center gap-2">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={image.preview} alt="Ausgewähltes Foto" className="h-16 rounded-lg" />
          <button onClick={() => setImage(null)} className="text-sm text-muted hover:underline">
            entfernen
          </button>
        </div>
      )}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        className="mt-3 flex gap-2"
      >
        <input
          ref={fileInput}
          type="file"
          accept="image/*"
          capture="environment"
          className="hidden"
          onChange={(e) => {
            pickImage(e.target.files?.[0]);
            e.target.value = "";
          }}
        />
        <button
          type="button"
          onClick={() => fileInput.current?.click()}
          className="rounded-xl border border-border px-3 text-lg hover:bg-surface-2"
          aria-label="Foto vom Essen"
          title="Foto vom Essen"
        >
          📷
        </button>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={image ? "Was ist drauf? (optional)" : "Schreib dem Gehirn …"}
          className="min-w-0 flex-1 rounded-xl border border-border bg-background px-4 py-3 text-sm outline-none focus:border-accent"
        />
        <button
          disabled={busy || (!input.trim() && !image)}
          className="rounded-xl bg-accent px-4 font-bold text-accent-fg disabled:opacity-50"
          aria-label="Senden"
        >
          ➤
        </button>
      </form>
    </section>
  );
}
