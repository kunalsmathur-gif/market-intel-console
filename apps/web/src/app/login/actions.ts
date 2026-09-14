"use server";

import { headers } from "next/headers";
import { redirect } from "next/navigation";

import { supabaseEnv } from "@/lib/supabase/env";
import { createClient } from "@/lib/supabase/server";

export type LoginState = { status: "idle" | "sent" | "error"; message?: string };

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export async function sendMagicLink(_: LoginState, formData: FormData): Promise<LoginState> {
  if (!supabaseEnv()) {
    return { status: "error", message: "Sign-in isn't set up yet: add the Supabase keys to .env.local." };
  }
  const email = String(formData.get("email") ?? "").trim().toLowerCase();
  if (!EMAIL.test(email)) return { status: "error", message: "Enter a valid email address." };

  const origin = (await headers()).get("origin") ?? "";
  const supabase = await createClient();
  // shouldCreateUser: false keeps sign-up closed; only existing accounts get a link.
  await supabase.auth.signInWithOtp({
    email,
    options: { shouldCreateUser: false, emailRedirectTo: `${origin}/auth/confirm` },
  });
  // Same answer either way, so the form doesn't reveal which emails are allowed.
  return { status: "sent", message: "If this email can sign in, a link is on its way." };
}

// Sends the browser to Google through Supabase. Google returns to /auth/confirm with a code.
// Access still depends on the owner allowlist, so any other Google account sees nothing.
export async function signInWithGoogle(): Promise<never> {
  if (!supabaseEnv()) redirect("/login?error=setup");
  const origin = (await headers()).get("origin") ?? "";
  const supabase = await createClient();
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: "google",
    options: { redirectTo: `${origin}/auth/confirm` },
  });
  redirect(error || !data.url ? "/login?error=google" : data.url);
}
