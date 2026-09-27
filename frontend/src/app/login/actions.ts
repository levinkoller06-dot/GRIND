"use server";

import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";

export type AuthState = { error?: string; message?: string };

function readForm(formData: FormData) {
  return {
    email: String(formData.get("email") ?? "").trim(),
    password: String(formData.get("password") ?? ""),
  };
}

export async function signIn(_: AuthState, formData: FormData): Promise<AuthState> {
  const { email, password } = readForm(formData);
  const supabase = await createClient();
  const { error } = await supabase.auth.signInWithPassword({ email, password });
  if (error) return { error: "E-Mail oder Passwort falsch." };
  redirect("/");
}

export async function signUp(_: AuthState, formData: FormData): Promise<AuthState> {
  const { email, password } = readForm(formData);
  const name = String(formData.get("name") ?? "").trim();
  if (password.length < 8) return { error: "Passwort muss mindestens 8 Zeichen haben." };

  const origin = (await headers()).get("origin") ?? "";
  const supabase = await createClient();
  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    options: {
      emailRedirectTo: `${origin}/auth/callback`,
      data: { display_name: name || null },
    },
  });
  if (error) return { error: error.message };

  // Ist die E-Mail-Bestätigung in Supabase aus, gibt es sofort eine Session.
  if (data.session) redirect("/");
  return { message: "Fast geschafft! Bestätige deine E-Mail über den Link, den wir dir geschickt haben." };
}

export async function signOut() {
  const supabase = await createClient();
  await supabase.auth.signOut();
  redirect("/login");
}
