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
    <section className="flex h-[70dvh] flex-col rounded-2xl border bg-surface p-5 md:h-full md:min-h-0">
      <header className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="flex items-center gap-2 text-lg font-bold tracking-tight">
            <span className="relative flex size-2.5">
              <span className="absolute inline-flex size-full animate-ping rounded-full bg-accent opacity-60" />
              <span className="relative inline-flex size-2.5 rounded-full bg-accent" />
            </span>
            GRIND AI
          </h2>
          <p className="text-xs text-muted">Dein smarter Assistent</p>
        </div>
        <span
          aria-hidden
          className={`size-9 rounded-full bg-[radial-gradient(circle_at_35%_30%,#f7fee7,#bef264_45%,#65a30d)] shadow-[0_0_24px_-2px_var(--glow)] transition-transform duration-700 ${busy ? "scale-110 animate-pulse" : ""}`}
        />
      </header>

      <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto pr-1">
        {messages.length === 0 && !busy && (
          <div className="msg-in rounded-2xl bg-surface-2/70 p-4 text-sm text-muted">
            Schreib einfach, was ansteht. Ich sortiere es für dich ein.
          </div>
        )}
        {messages.map((m, i) => (
          <div
            key={m.id ?? `local-${i}`}
            className={`msg-in selectable max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed shadow-[var(--shadow)] ${
              m.role === "user"
                ? "self-end rounded-br-md bg-accent/20 text-foreground"
                : "self-start rounded-bl-md bg-[var(--glass-strong)]"
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
          <div className="msg-in typing self-start rounded-2xl rounded-bl-md bg-[var(--glass-strong)] px-4 py-3 text-muted shadow-[var(--shadow)]" aria-label="denkt nach">
            <span />
            <span />
            <span />
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
              className="rounded-full border border-border bg-[var(--glass)] px-3 py-1.5 text-xs text-muted transition hover:-translate-y-0.5 hover:border-accent hover:text-foreground"
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
        className="mt-4 flex items-center gap-2 rounded-2xl border border-border bg-[var(--glass-strong)] p-1.5 pl-2 shadow-[var(--shadow)] transition focus-within:border-accent focus-within:shadow-[0_0_0_4px_var(--glow)]"
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
          className="grid size-10 shrink-0 place-items-center rounded-xl text-lg transition hover:bg-surface-2"
          aria-label="Foto vom Essen"
          title="Foto vom Essen"
        >
          📷
        </button>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={image ? "Was ist drauf? (optional)" : "Nachricht an GRIND AI …"}
          className="min-w-0 flex-1 bg-transparent px-2 py-2.5 text-sm outline-none"
        />
        <button
          disabled={busy || (!input.trim() && !image)}
          className="glow-button grid size-11 shrink-0 place-items-center rounded-full bg-accent text-lg font-bold text-accent-fg disabled:opacity-40"
          aria-label="Senden"
        >
          ↑
        </button>
      </form>
    </section>
  );
}
