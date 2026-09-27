export function SetupNotice() {
  return (
    <main className="mx-auto flex min-h-dvh max-w-lg flex-col justify-center gap-4 p-6">
      <h1 className="text-3xl font-black">
        GRIND<span className="text-accent">.</span>
      </h1>
      <p>Supabase ist noch nicht eingerichtet.</p>
      <ol className="list-decimal space-y-1 pl-5 text-muted">
        <li>
          <code>frontend/.env.local.example</code> nach <code>frontend/.env.local</code> kopieren
        </li>
        <li>URL und Publishable Key aus Supabase eintragen</li>
        <li>Dev-Server neu starten</li>
      </ol>
      <p className="text-sm text-muted">Details: docs/SETUP.md</p>
    </main>
  );
}
