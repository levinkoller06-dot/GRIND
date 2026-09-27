"use server";

import { revalidatePath } from "next/cache";
import { createClient } from "@/lib/supabase/server";

async function remove(table: "meals" | "workouts", id: string) {
  const supabase = await createClient();
  // RLS sorgt dafür, dass nur eigene Einträge gelöscht werden können
  await supabase.from(table).delete().eq("id", id);
  revalidatePath("/", "layout");
}

export async function deleteMeal(id: string) {
  await remove("meals", id);
}

export async function deleteWorkout(id: string) {
  await remove("workouts", id);
}
