import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { connection } from "next/server";

import { requireViewer } from "@/lib/auth";
import { createClient } from "@/lib/supabase/server";
import { supabaseEnv } from "@/lib/supabase/env";

import { UpstoxTokenForm } from "./upstox-token-form";

export const metadata: Metadata = { title: "Settings" };

type CredentialStatus = { expires_at: string; updated_at: string } | null;

export default async function SettingsPage() {
  await connection(); // status depends on the signed-in user and today's saved token
  if (!supabaseEnv()) redirect("/login");
  const viewer = await requireViewer();
  if (!viewer.isOwner) redirect("/");

  const supabase = await createClient();
  const { data } = await supabase
    .rpc("provider_credential_status", { p_provider: "upstox" })
    .maybeSingle();
  const status = (data ?? null) as CredentialStatus;
  const expired = status ? new Date(status.expires_at).getTime() <= new Date().getTime() : true;

  return (
    <div className="mx-auto flex w-full max-w-sm flex-1 flex-col px-4 py-8">
      <Link href="/" className="text-sm text-text-2 hover:text-text">
        ← Today
      </Link>
      <h1 className="mt-4 text-xl font-semibold">Settings</h1>

      <section className="mt-6 rounded-xl border border-line bg-panel p-4">
        <h2 className="font-semibold">Upstox connection</h2>
        <p className="mt-1 text-sm text-text-2">
          Upstox access tokens expire daily at 03:30 IST with no refresh. Paste a fresh one each
          trading day — the worker reads it straight from the database, no redeploy needed.
        </p>

        <p className="mt-3 text-sm" role="status">
          {status && !expired ? (
            <span className="text-up">
              Connected — expires{" "}
              <span className="font-mono">
                {new Date(status.expires_at).toLocaleString("en-IN", {
                  timeZone: "Asia/Kolkata",
                  dateStyle: "medium",
                  timeStyle: "short",
                })}
              </span>{" "}
              IST
            </span>
          ) : status ? (
            <span className="text-down">Token expired — paste a new one below</span>
          ) : (
            <span className="text-text-2">Not connected yet</span>
          )}
        </p>

        <div className="mt-4">
          <UpstoxTokenForm />
        </div>
      </section>
    </div>
  );
}
