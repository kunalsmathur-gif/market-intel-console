import { NextResponse, type NextRequest } from "next/server";

import { createClient } from "@/lib/supabase/server";

// POST only, so a link or prefetch can't sign you out. scope=global ends every session.
export async function POST(request: NextRequest) {
  const form = await request.formData();
  const scope = form.get("scope") === "global" ? "global" : "local";

  const supabase = await createClient();
  await supabase.auth.signOut({ scope });

  const login = request.nextUrl.clone();
  login.pathname = "/login";
  login.search = "";
  return NextResponse.redirect(login, { status: 303 });
}
