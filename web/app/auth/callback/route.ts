import { NextResponse, type NextRequest } from "next/server";
import { createClient } from "@/lib/supabase/server";

export async function GET(request: NextRequest) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  const requestedNext = searchParams.get("next") ?? "/dashboard";
  const nextUrl = new URL(requestedNext, origin);
  const next = requestedNext.startsWith("/") && nextUrl.origin === origin
    ? `${nextUrl.pathname}${nextUrl.search}${nextUrl.hash}`
    : "/dashboard";
  if (code) {
    const supabase = await createClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) return NextResponse.redirect(new URL(next, origin));
  }
  return NextResponse.redirect(`${origin}/sign-in?error=auth`);
}
