"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { SETTINGS_TAB, TABS } from "./tabs";

function isActive(pathname: string, href: string) {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

export function Sidebar() {
  const pathname = usePathname();
  return (
    <nav className="hidden md:flex md:w-56 shrink-0 flex-col gap-1 border-r border-border bg-surface p-4">
      <div className="mb-6 px-2 text-2xl font-black tracking-tight">
        GRIND<span className="text-accent">.</span>
      </div>
      {[...TABS, SETTINGS_TAB].map((tab) => (
        <Link
          key={tab.href}
          href={tab.href}
          className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
            isActive(pathname, tab.href)
              ? "bg-accent text-accent-fg"
              : "text-muted hover:bg-surface-2 hover:text-foreground"
          }`}
        >
          <span aria-hidden>{tab.icon}</span>
          {tab.label}
        </Link>
      ))}
    </nav>
  );
}

export function BottomBar() {
  const pathname = usePathname();
  return (
    <nav className="fixed inset-x-0 bottom-0 z-10 border-t border-border bg-surface/95 backdrop-blur md:hidden pb-[env(safe-area-inset-bottom)]">
      <ul className="flex overflow-x-auto">
        {TABS.map((tab) => (
          <li key={tab.href} className="min-w-16 flex-1">
            <Link
              href={tab.href}
              className={`flex flex-col items-center gap-0.5 py-2 text-[11px] font-medium ${
                isActive(pathname, tab.href) ? "text-accent" : "text-muted"
              }`}
            >
              <span className="text-lg" aria-hidden>
                {tab.icon}
              </span>
              {tab.label}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
