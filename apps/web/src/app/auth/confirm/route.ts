import type { EmailOtpType } from "@supabase/supabase-js";
import { NextResponse, type NextRequest } from "next/server";

import { createClient } from "@/lib/supabase/server";

// Lands here from the magic link or from Google. Handles:
// ?token_hash=…&type=email (custom email template), ?code=… (PKCE redirect from either),
// and ?error=… (Google or Supabase refused the sign-in, e.g. an account that isn't the owner's).
export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const tokenHash = searchParams.get("token_hash");
  const type = searchParams.get("type") as EmailOtpType | null;
  const code = searchParams.get("code");

  let ok = false;
  let failure = "link";
  if (searchParams.has("error")) {
    failure = "provider";
  } else if (tokenHash && type) {
    const supabase = await createClient();
    ok = !(await supabase.auth.verifyOtp({ type, token_hash: tokenHash })).error;
  } else if (code) {
    const supabase = await createClient();
    ok = !(await supabase.auth.exchangeCodeForSession(code)).error;
    failure = "incomplete";
  }

  const target = request.nextUrl.clone();
  target.search = "";
  target.pathname = ok ? "/" : "/login";
  if (!ok) target.searchParams.set("error", failure);
  return NextResponse.redirect(target);
}
