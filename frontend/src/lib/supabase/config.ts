export const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
export const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ?? "";
export const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const isSupabaseConfigured = Boolean(supabaseUrl && supabaseKey);
