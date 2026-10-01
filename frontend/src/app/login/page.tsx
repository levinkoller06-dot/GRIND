"use client";

import { useActionState, useState } from "react";
import { signIn, signUp, type AuthState } from "./actions";

export default function LoginPage() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [state, formAction, pending] = useActionState<AuthState, FormData>(
    mode === "login" ? signIn : signUp,
    {},
  );

  const input =
    "w-full rounded-xl border border-border bg-[var(--glass-strong)] px-4 py-3 text-sm outline-none transition focus:border-accent focus:shadow-[0_0_0_4px_var(--glow)]";

  return (
    <main className="stagger mx-auto flex min-h-dvh w-full max-w-sm flex-col justify-center gap-6 p-6">
      <div>
        <h1 className="text-6xl font-black tracking-tighter">
          GRIND<span className="text-accent">.</span>
        </h1>
        <p className="text-muted">Schule. Gym. Leben.</p>
      </div>

      <div className="glass flex flex-col gap-4 rounded-3xl border p-5">
      <div className="grid grid-cols-2 rounded-xl bg-surface-2/70 p-1 text-sm font-medium">
        {(["login", "register"] as const).map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => setMode(m)}
            className={`rounded-lg py-2 transition-all duration-300 ${mode === m ? "bg-surface shadow-sm" : "text-muted hover:text-foreground"}`}
          >
            {m === "login" ? "Anmelden" : "Registrieren"}
          </button>
        ))}
      </div>

      <form action={formAction} className="flex flex-col gap-3">
        {mode === "register" && <input name="name" placeholder="Name" className={input} autoComplete="name" />}
        <input name="email" type="email" required placeholder="E-Mail" className={input} autoComplete="email" />
        <input
          name="password"
          type="password"
          required
          placeholder="Passwort"
          className={input}
          autoComplete={mode === "login" ? "current-password" : "new-password"}
        />
        <button
          disabled={pending}
          className="glow-button rounded-xl bg-accent py-3 font-bold text-accent-fg disabled:opacity-60"
        >
          {pending ? "…" : mode === "login" ? "Anmelden" : "Konto erstellen"}
        </button>
        {state.error && <p className="text-sm text-red-500">{state.error}</p>}
        {state.message && <p className="text-sm text-accent">{state.message}</p>}
      </form>
      </div>
    </main>
  );
}
