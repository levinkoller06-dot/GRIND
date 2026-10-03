"use server";

import { revalidatePath } from "next/cache";
import { createClient } from "@/lib/supabase/server";

export async function saveProfile(formData: FormData) {
  const supabase = await createClient();
  const { data } = await supabase.auth.getClaims();
  const userId = data?.claims?.sub;
  if (!userId) return;

  const scale = formData.get("grade_scale");
  const name = String(formData.get("display_name") ?? "").trim();
  const goal = (key: string) => {
    const n = parseInt(String(formData.get(key) ?? ""), 10);
    return Number.isFinite(n) && n > 0 ? n : null;
  };

  await supabase
    .from("profiles")
    .update({
      display_name: name || null,
      grade_scale: scale === "de" ? "de" : "ch",
      goal_kcal: goal("goal_kcal"),
      goal_protein_g: goal("goal_protein_g"),
    })
    .eq("id", userId);

  revalidatePath("/", "layout");
}

/** Uhrzeit für den Morgen-Check (leer = aus). Eigene Aktion, damit das Profil auch ohne
 *  die Zeitplan-Migration speicherbar bleibt. */
export async function saveMorningCheck(formData: FormData) {
  const supabase = await createClient();
  const { data } = await supabase.auth.getClaims();
  const userId = data?.claims?.sub;
  if (!userId) return;

  const on = formData.get("morning_on") === "on";
  const time = String(formData.get("morning_check_time") ?? "");
  await supabase
    .from("profiles")
    .update({ morning_check_time: on && /^\d{2}:\d{2}$/.test(time) ? time : null })
    .eq("id", userId);

  revalidatePath("/einstellungen");
}
