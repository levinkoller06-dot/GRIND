"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { apiUrl } from "@/lib/supabase/config";

type Status = { state: "loading" } | { state: "ok"; userId: string } | { state: "error"; message: string };

export function BackendStatus() {
  const [status, setStatus] = useState<Status>({ state: "loading" });

  useEffect(() => {
    async function check() {
      const { data } = await createClient().auth.getSession();
      const token = data.session?.access_token;
      if (!token) return setStatus({ state: "error", message: "Nicht angemeldet" });

      try {
        const res = await fetch(`${apiUrl}/me`, { headers: { Authorization: `Bearer ${token}` } });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const body = await res.json();
        setStatus({ state: "ok", userId: body.user_id });
      } catch (e) {
        setStatus({ state: "error", message: e instanceof Error ? e.message : "Unbekannter Fehler" });
      }
    }
    check();
  }, []);

  const dot =
    status.state === "ok" ? "bg-green-500" : status.state === "error" ? "bg-red-500" : "bg-yellow-500";

  return (
    <p className="flex items-center gap-2 text-xs text-muted">
      <span className={`size-2 rounded-full ${dot}`} />
      Backend:{" "}
      {status.state === "loading" && "prüfe …"}
      {status.state === "ok" && "verbunden"}
      {status.state === "error" && `nicht erreichbar (${status.message})`}
    </p>
  );
}
