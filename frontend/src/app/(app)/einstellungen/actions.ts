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

  await supabase
    .from("profiles")
    .update({
      display_name: name || null,
      grade_scale: scale === "de" ? "de" : "ch",
    })
    .eq("id", userId);

  revalidatePath("/", "layout");
}
