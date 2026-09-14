import type { Metadata } from "next";

import { Wordmark } from "@/components/wordmark";
import { supabaseEnv } from "@/lib/supabase/env";

import { signInWithGoogle } from "./actions";
import { LoginForm } from "./login-form";

export const metadata: Metadata = { title: "Sign in" };

// Set by /auth/confirm and the Google action when sign-in doesn't complete.
const ERRORS: Record<string, string> = {
  link: "That sign-in link has expired or was already used. Request a new one below.",
  incomplete: "Sign-in didn't complete. Start again in this browser: the link or Google has to finish where it began.",
  provider: "Google sign-in didn't complete. Only the owner's account can sign in. Try again, or use the email link.",
  google: "Google sign-in isn't available right now. Use the email link instead.",
  setup: "Sign-in isn't set up yet: add the Supabase keys to .env.local.",
};

export default async function LoginPage({ searchParams }: PageProps<"/login">) {
  const configured = supabaseEnv() !== null;
  const { error } = await searchParams;
  const errorMessage = typeof error === "string" ? ERRORS[error] : undefined;

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
        {errorMessage && (
          <p role="alert" className="mb-4 rounded-md border border-down/40 px-3 py-2 text-sm text-down">
            {errorMessage}
          </p>
        )}

        <form action={signInWithGoogle}>
          <button
            type="submit"
            className="flex w-full cursor-pointer items-center justify-center gap-3 rounded-md border border-line bg-bg px-4 py-2.5 font-medium text-text transition-colors duration-200 hover:border-signal focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-signal"
          >
            <GoogleMark />
            Continue with Google
          </button>
        </form>

        <div className="my-5 flex items-center gap-3 text-xs text-text-3" aria-hidden="true">
          <span className="h-px flex-1 bg-line" />
          or email me a link
          <span className="h-px flex-1 bg-line" />
        </div>

        <LoginForm />
      </div>
    </main>
  );
}

function GoogleMark() {
  return (
    <svg aria-hidden="true" width="18" height="18" viewBox="0 0 48 48">
      <path fill="#FFC107" d="M43.6 20.1H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 8 3l5.7-5.7C34 6.1 29.3 4 24 4 13 4 4 13 4 24s9 20 20 20 20-9 20-20c0-1.3-.1-2.6-.4-3.9z" />
      <path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.8 1.2 8 3l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z" />
      <path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-7.9l-6.5 5C9.5 39.6 16.2 44 24 44z" />
      <path fill="#1976D2" d="M43.6 20.1H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C37 39.2 44 34 44 24c0-1.3-.1-2.6-.4-3.9z" />
    </svg>
  );
}
