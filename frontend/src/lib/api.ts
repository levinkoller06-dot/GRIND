import { createClient } from "@/lib/supabase/client";
import { apiUrl } from "@/lib/supabase/config";

export type ChatMessage = { id?: number; role: "user" | "assistant"; content: string };

export type EventPayload = {
  titel: string;
  datum: string;
  uhrzeit?: string;
  ende_uhrzeit?: string;
  art?: string;
  notiz?: string;
  ort?: string;
  mit?: string[];
};

export type PendingAction = {
  id: string;
  kind: string;
  payload: EventPayload;
  status: string;
  created_at: string;
};

export type ChatResponse = { reply: string; pending: PendingAction[]; tools: string[] };

export class ApiError extends Error {}

/** Ruft das Python-Backend mit dem Login-Token des Nutzers auf. */
export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const { data } = await createClient().auth.getSession();
  const token = data.session?.access_token;
  if (!token) throw new ApiError("Nicht angemeldet");

  let res: Response;
  try {
    res = await fetch(`${apiUrl}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
        ...init.headers,
      },
    });
  } catch {
    throw new ApiError("Backend nicht erreichbar");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new ApiError(body?.detail ?? `Fehler ${res.status}`);
  }
  return res.json();
}
