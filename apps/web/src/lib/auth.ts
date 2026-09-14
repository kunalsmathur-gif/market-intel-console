import "server-only";

import { redirect } from "next/navigation";

import { createClient } from "./supabase/server";

export type Viewer = { email: string; isOwner: boolean };

// V0 is owner-only. The allowlist lives in the database (public.allowed_users), and RLS
// enforces it on every table, so this check only decides what the page shows.
export async function requireViewer(): Promise<Viewer> {
  const supabase = await createClient();
  const { data } = await supabase.auth.getClaims();
  const email = data?.claims?.email;
  if (!email) redirect("/login");

  const { data: isOwner, error } = await supabase.rpc("is_owner");
  return { email, isOwner: !error && isOwner === true };
}
