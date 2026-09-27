import type { Tab } from "./tabs";

export function Placeholder({ tab, phase }: { tab: Tab; phase: string }) {
  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-black tracking-tight">
          {tab.icon} {tab.label}
        </h1>
        <p className="text-muted">{tab.description}</p>
      </header>
      <div className="rounded-2xl border border-dashed border-border bg-surface p-8 text-center text-muted">
        Kommt in {phase}.
      </div>
    </div>
  );
}
