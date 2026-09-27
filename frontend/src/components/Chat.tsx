"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api, type ChatMessage, type ChatResponse, type PendingAction } from "@/lib/api";
import { PendingCard } from "./PendingCard";

const EXAMPLES = [
  "Donnerstag ist Mathetest über Brüche",
  "Hab ne 2 in Englisch bekommen",
  "Wie steh ich in Mathe?",
];

export function Chat() {
  const router = useRouter();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [pending, setPending] = useState<PendingAction[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottom = useRef<HTMLDivElement>(null);

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
    const message = text.trim();
    if (!message || busy) return;
    setInput("");
    setError(null);
    setBusy(true);
    setMessages((m) => [...m, { role: "user", content: message }]);
    try {
      const res = await api<ChatResponse>("/chat", {
        method: "POST",
        body: JSON.stringify({ message }),
      });
      setMessages((m) => [...m, { role: "assistant", content: res.reply }]);
      setPending((p) => [...p, ...res.pending]);
      if (res.tools.length) router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Fehler");
    } finally {
      setBusy(false);
    }
  }

  function onDecided(id: string) {
    setPending((p) => p.filter((a) => a.id !== id));
    router.refresh();
  }

  return (
    <section className="rounded-2xl border border-border bg-surface p-4">
      <h2 className="mb-3 font-bold">🧠 Gehirn</h2>

      <div className="flex max-h-[28rem] flex-col gap-2 overflow-y-auto pr-1">
        {messages.length === 0 && !busy && (
          <div className="rounded-xl bg-surface-2 p-3 text-sm text-muted">
            Schreib einfach, was ansteht. Ich sortiere es für dich ein.
          </div>
        )}
        {messages.map((m, i) => (
          <div
            key={m.id ?? `local-${i}`}
            className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-3 py-2 text-sm ${
              m.role === "user"
                ? "self-end rounded-br-sm bg-accent text-accent-fg"
                : "self-start rounded-bl-sm bg-surface-2"
            }`}
          >
            {m.content}
          </div>
        ))}
        {busy && (
          <div className="self-start rounded-2xl rounded-bl-sm bg-surface-2 px-3 py-2 text-sm text-muted">
            denkt nach …
          </div>
        )}
        {pending.map((a) => (
          <PendingCard key={a.id} action={a} onDone={onDecided} />
        ))}
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

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        className="mt-3 flex gap-2"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Schreib dem Gehirn …"
          className="flex-1 rounded-xl border border-border bg-background px-4 py-3 text-sm outline-none focus:border-accent"
        />
        <button
          disabled={busy || !input.trim()}
          className="rounded-xl bg-accent px-4 font-bold text-accent-fg disabled:opacity-50"
          aria-label="Senden"
        >
          ➤
        </button>
      </form>
    </section>
  );
}
