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
