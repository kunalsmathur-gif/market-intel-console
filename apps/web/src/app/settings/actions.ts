"use server";

import { revalidatePath } from "next/cache";

import { requireViewer } from "@/lib/auth";
import { createClient } from "@/lib/supabase/server";

export type SettingsState = { status: "idle" | "saved" | "error"; message?: string };

const PROVIDER = "upstox";

// Upstox access tokens always expire at 03:30 IST the next day, with no refresh token
// (PRD §9.3 [R42]), so the owner only ever pastes the token itself — the expiry is
// computed here, not typed in.
function nextUpstoxExpiry(now: Date): Date {
  const IST_OFFSET_MINUTES = 5 * 60 + 30;
  const istNow = new Date(now.getTime() + IST_OFFSET_MINUTES * 60_000);
  const expiryIst = new Date(
    Date.UTC(istNow.getUTCFullYear(), istNow.getUTCMonth(), istNow.getUTCDate(), 3, 30, 0)
  );
  if (expiryIst.getTime() <= istNow.getTime()) {
    expiryIst.setUTCDate(expiryIst.getUTCDate() + 1);
  }
  return new Date(expiryIst.getTime() - IST_OFFSET_MINUTES * 60_000);
}

export async function saveUpstoxToken(_: SettingsState, formData: FormData): Promise<SettingsState> {
  const viewer = await requireViewer();
  if (!viewer.isOwner) return { status: "error", message: "Only the owner can set this." };

  const accessToken = String(formData.get("access_token") ?? "").trim();
  if (!accessToken) return { status: "error", message: "Paste today's Upstox access token." };

  const expiresAt = nextUpstoxExpiry(new Date());
  const supabase = await createClient();
  const { error } = await supabase.rpc("set_provider_credential", {
    p_provider: PROVIDER,
    p_access_token: accessToken,
    p_expires_at: expiresAt.toISOString(),
  });
  if (error) return { status: "error", message: "Couldn't save the token. Try again." };

  revalidatePath("/settings");
  return { status: "saved", message: `Saved. Expires ${expiresAt.toLocaleString("en-IN", { timeZone: "Asia/Kolkata", dateStyle: "medium", timeStyle: "short" })} IST.` };
}
