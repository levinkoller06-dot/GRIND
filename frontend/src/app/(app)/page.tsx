import { createClient } from "@/lib/supabase/server";
import { BackendStatus } from "@/components/BackendStatus";

const OVERVIEW = [
  { icon: "💪", label: "Training heute", value: "–" },
  { icon: "📝", label: "Nächster Test", value: "–" },
  { icon: "🍗", label: "Protein", value: "– / – g" },
  { icon: "📬", label: "Neue Mails", value: "–" },
];

export default async function StartPage() {
  const supabase = await createClient();
  const { data } = await supabase.auth.getClaims();
  const userId = data?.claims?.sub;

  const { data: profile } = userId
    ? await supabase.from("profiles").select("display_name").eq("id", userId).maybeSingle()
    : { data: null };

  const name = profile?.display_name ?? data?.claims?.email ?? "du";
  const today = new Date().toLocaleDateString("de-DE", {
    weekday: "long",
    day: "numeric",
    month: "long",
  });

  return (
    <div className="space-y-6">
      <header>
        <p className="text-sm text-muted">{today}</p>
        <h1 className="text-3xl font-black tracking-tight">Hey {name} 👋</h1>
      </header>

      <section className="grid grid-cols-2 gap-3">
        {OVERVIEW.map((item) => (
          <div key={item.label} className="rounded-2xl border border-border bg-surface p-4">
            <div className="text-sm text-muted">
              {item.icon} {item.label}
            </div>
            <div className="mt-1 text-xl font-bold">{item.value}</div>
          </div>
        ))}
      </section>

      <section className="rounded-2xl border border-border bg-surface p-4">
        <h2 className="mb-3 font-bold">🧠 Gehirn</h2>
        <div className="mb-3 rounded-xl bg-surface-2 p-3 text-sm text-muted">
          Hier kommt in Phase 1 der Chat hin. Dann kannst du einfach schreiben:
          „Hab 3×10 Liegestütze gemacht und Donnerstag ist Mathetest.“
        </div>
        <input
          disabled
          placeholder="Schreib dem Gehirn …"
          className="w-full rounded-xl border border-border bg-background px-4 py-3 text-sm disabled:opacity-60"
        />
      </section>

      <BackendStatus />
    </div>
  );
}
