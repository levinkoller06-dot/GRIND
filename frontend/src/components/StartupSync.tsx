"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { api } from "@/lib/api";
import { loadInbox } from "@/lib/inbox";

/** Sobald die App offen ist: Postfach laden und Moodle abgleichen (im Hintergrund). */
export function StartupSync() {
  const router = useRouter();
  useEffect(() => {
    loadInbox().catch(() => {});
    api<{ neu?: number; geaendert?: number; entfernt?: number }>("/moodle/sync", { method: "POST" })
      .then((r) => {
        // Neue Abgaben/Prüfungen gleich anzeigen
        if (r.neu || r.geaendert || r.entfernt) router.refresh();
      })
      .catch(() => {});
  }, [router]);
  return null;
}
