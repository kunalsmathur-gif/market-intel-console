import type { Metadata } from "next";

import { Wordmark } from "@/components/wordmark";
import { supabaseEnv } from "@/lib/supabase/env";

import { LoginForm } from "./login-form";

export const metadata: Metadata = { title: "Sign in" };

export default function LoginPage() {
  const configured = supabaseEnv() !== null;

  return (
    <main className="flex flex-1 items-center justify-center px-4 py-12">
      <div className="w-full max-w-sm rounded-xl border border-line bg-panel p-6">
        <Wordmark className="text-2xl" />
        <p className="mt-1 text-sm text-text-2">Verified before the bell.</p>
        <h1 className="mt-6 text-lg font-semibold">Sign in</h1>
        <p className="mt-1 mb-4 text-sm text-text-2">Owner access only. There is no sign-up.</p>
        {!configured && (
          <p role="status" className="mb-4 rounded-md border border-withheld/40 px-3 py-2 text-sm text-withheld">
            Supabase isn&apos;t configured. Copy <code className="font-mono">.env.example</code> to{" "}
            <code className="font-mono">.env.local</code> and add the project URL and publishable key.
          </p>
        )}
        <LoginForm />
      </div>
    </main>
  );
}
