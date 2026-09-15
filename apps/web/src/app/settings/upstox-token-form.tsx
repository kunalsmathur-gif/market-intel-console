"use client";

import { useActionState } from "react";

import { saveUpstoxToken, type SettingsState } from "./actions";

const initial: SettingsState = { status: "idle" };

export function UpstoxTokenForm() {
  const [state, action, pending] = useActionState(saveUpstoxToken, initial);

  return (
    <form action={action} className="flex flex-col gap-3">
      <label htmlFor="access_token" className="text-sm font-medium text-text-2">
        Today&apos;s Upstox access token
      </label>
      <input
        id="access_token"
        name="access_token"
        type="password"
        autoComplete="off"
        spellCheck={false}
        required
        className="rounded-md border border-line bg-bg px-3 py-2.5 font-mono text-sm text-text outline-none transition-colors duration-200 focus-visible:border-signal focus-visible:ring-2 focus-visible:ring-signal/40"
      />
      <button
        type="submit"
        disabled={pending}
        className="cursor-pointer rounded-md bg-signal px-4 py-2.5 font-semibold text-on-signal transition-opacity duration-200 hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-signal disabled:cursor-wait disabled:opacity-60"
      >
        {pending ? "Saving…" : "Save token"}
      </button>
      <p aria-live="polite" className={state.status === "error" ? "text-sm text-down" : "text-sm text-text-2"}>
        {state.message}
      </p>
    </form>
  );
}
