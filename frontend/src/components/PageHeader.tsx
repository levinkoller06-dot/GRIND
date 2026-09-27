import type { ReactNode } from "react";
import type { Tab } from "./tabs";

export function PageHeader({ tab, children }: { tab: Tab; children?: ReactNode }) {
  return (
    <header className="mb-4 flex flex-wrap items-end justify-between gap-2">
      <div>
        <h1 className="text-2xl font-black tracking-tight md:text-3xl">
          {tab.icon} {tab.label}
        </h1>
        <p className="text-sm text-muted">{tab.description}</p>
      </div>
      {children}
    </header>
  );
}
