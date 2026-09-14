import { redirect } from "next/navigation";
import { connection } from "next/server";

import { Wordmark } from "@/components/wordmark";
import { requireViewer } from "@/lib/auth";
import { REPORTS, formatIstTime, todayInIst, type PublishedReport } from "@/lib/reports";
import { supabaseEnv } from "@/lib/supabase/env";
import { createClient } from "@/lib/supabase/server";

export default async function TodayPage() {
  await connection(); // always per request: it depends on the signed-in user
  if (!supabaseEnv()) redirect("/login");
  const viewer = await requireViewer();
  const today = todayInIst();

  let published: PublishedReport[] = [];
  if (viewer.isOwner) {
    const supabase = await createClient();
    const { data } = await supabase
      .from("reports")
      .select("report_type, trading_date, version, title, published_at")
      .eq("trading_date", today)
      .order("published_at", { ascending: false });
    published = (data ?? []) as PublishedReport[];
  }

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-1 flex-col px-4 py-4">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-line pb-3">
        <div className="flex items-baseline gap-3">
          <Wordmark className="text-xl" />
          <span className="font-mono text-sm text-text-2">{today} IST</span>
        </div>
        <form action="/auth/signout" method="post" className="flex items-center gap-2 text-sm">
          <span className="hidden text-text-3 sm:inline">{viewer.email}</span>
          <button name="scope" value="local" className="cursor-pointer rounded-md border border-line px-3 py-1.5 transition-colors duration-200 hover:border-signal focus-visible:outline-2 focus-visible:outline-signal">
            Sign out
          </button>
          <button name="scope" value="global" className="cursor-pointer rounded-md px-3 py-1.5 text-text-2 transition-colors duration-200 hover:text-text focus-visible:outline-2 focus-visible:outline-signal">
            Sign out everywhere
          </button>
        </form>
      </header>

      {viewer.isOwner ? (
        <main className="py-6">
          <h1 className="text-2xl font-semibold tracking-tight">Today</h1>
          <ul className="mt-4 grid gap-3 sm:grid-cols-2">
            {REPORTS.map((report) => {
              const latest = published.find((p) => p.report_type === report.type);
              return (
                <li key={report.type} className="rounded-xl border border-line bg-panel p-4">
                  <div className="flex items-baseline justify-between gap-2">
                    <h2 className="font-semibold">{report.title}</h2>
                    <span className="font-mono text-xs text-text-3">ready by {report.readyBy}</span>
                  </div>
                  {latest ? (
                    <p className="mt-2 text-sm text-up">
                      Published <span className="font-mono">{formatIstTime(latest.published_at)}</span>
                      {latest.version > 1 && <span className="text-text-2"> · v{latest.version}</span>}
                    </p>
                  ) : (
                    <p className="mt-2 text-sm text-text-2">Not published yet</p>
                  )}
                </li>
              );
            })}
          </ul>
        </main>
      ) : (
        <main className="py-10">
          <h1 className="text-xl font-semibold">This account can&apos;t open Citebell</h1>
          <p className="mt-2 text-text-2">Citebell is owner-only for now. Sign out and use the owner&apos;s email.</p>
        </main>
      )}

      <footer className="mt-auto border-t border-line pt-3 text-xs text-text-3">
        Market information for personal use, not investment advice.
      </footer>
    </div>
  );
}
