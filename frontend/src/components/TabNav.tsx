"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { SETTINGS_TAB, TABS } from "./tabs";

function isActive(pathname: string, href: string) {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

// Höhe eines Eintrags + Abstand (h-10 + gap-1), damit die Markierung genau darunter gleitet
const ITEM_STEP = 44;

export function Sidebar() {
  const pathname = usePathname();
  const items = [...TABS, SETTINGS_TAB];
  const active = items.findIndex((tab) => isActive(pathname, tab.href));

  return (
    <nav className="glass m-3 mr-0 hidden w-56 shrink-0 flex-col rounded-3xl border p-4 md:flex">
      <Link href="/" className="mb-8 px-3 pt-1 text-[1.65rem] font-black tracking-tighter">
        GRIND<span className="text-accent">.</span>
      </Link>
      <div className="relative flex flex-col gap-1">
        {active >= 0 && (
          <span
            aria-hidden
            className="absolute inset-x-0 top-0 h-10 rounded-xl bg-accent/15 transition-transform duration-500 ease-[cubic-bezier(0.2,0.8,0.2,1)]"
            style={{ transform: `translateY(${active * ITEM_STEP}px)` }}
          >
            <span className="absolute top-2 bottom-2 left-0 w-1 rounded-full bg-accent" />
          </span>
        )}
        {items.map((tab, i) => (
          <Link
            key={tab.href}
            href={tab.href}
            className={`relative flex h-10 items-center gap-3 rounded-xl px-3 text-sm transition-colors duration-300 ${
              i === active ? "font-semibold text-foreground" : "font-medium text-muted hover:text-foreground"
            }`}
          >
            <span
              aria-hidden
              className={`text-base transition-transform duration-300 ${i === active ? "scale-110" : "grayscale-[0.4]"}`}
            >
              {tab.icon}
            </span>
            {tab.label}
          </Link>
        ))}
      </div>
    </nav>
  );
}

export function BottomBar() {
  const pathname = usePathname();
  return (
    <nav className="glass fixed inset-x-2 bottom-2 z-10 rounded-2xl border md:hidden mb-[env(safe-area-inset-bottom)]">
      <ul className="flex overflow-x-auto">
        {TABS.map((tab) => {
          const on = isActive(pathname, tab.href);
          return (
            <li key={tab.href} className="min-w-16 flex-1">
              <Link
                href={tab.href}
                className={`relative flex flex-col items-center gap-0.5 py-2 text-[11px] font-medium transition-colors ${
                  on ? "text-foreground" : "text-muted"
                }`}
              >
                <span className={`text-lg transition-transform duration-300 ${on ? "-translate-y-0.5 scale-110" : ""}`} aria-hidden>
                  {tab.icon}
                </span>
                {tab.label}
                <span
                  className={`absolute bottom-0.5 h-1 w-1 rounded-full bg-accent transition-opacity duration-300 ${on ? "opacity-100" : "opacity-0"}`}
                />
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
