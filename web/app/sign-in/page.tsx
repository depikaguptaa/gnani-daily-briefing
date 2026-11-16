"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";

export default function SignInPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (new URLSearchParams(window.location.search).has("error")) {
      setError("That sign-in link expired or could not be verified. Request a fresh link below.");
    }
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const supabase = createClient();
    const requestedNext = new URLSearchParams(window.location.search).get("next") ?? "/dashboard";
    const nextUrl = new URL(requestedNext, window.location.origin);
    const next = requestedNext.startsWith("/") && nextUrl.origin === window.location.origin
      ? `${nextUrl.pathname}${nextUrl.search}${nextUrl.hash}`
      : "/dashboard";
    const callbackUrl = new URL("/auth/callback", window.location.origin);
    callbackUrl.searchParams.set("next", next);
    const { error: authError } = await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: callbackUrl.toString() },
    });
    setBusy(false);
    if (authError) setError(authError.message);
    else setSent(true);
  }

  return (
    <main className="signin-shell">
      <Link className="wordmark" href="/">daily<span>context</span></Link>
      <div className="signin-card">
        <p className="eyebrow">YOUR NEXT LISTEN IS CLOSE</p>
        <h1>{sent ? "Check your inbox." : "A fresh perspective,\nright on time."}</h1>
        <p>{sent ? `We sent a secure sign-in link to ${email}. Follow it to open your briefings.` : "Enter your email and we’ll send you a secure sign-in link. No password to remember."}</p>
        {!sent && <form onSubmit={submit} className="signin-form"><label htmlFor="email">Email address</label><input id="email" type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" /><button className="button button-dark" disabled={busy}>{busy ? "Sending link…" : "Email me a sign-in link"} <span aria-hidden="true">→</span></button></form>}
        {error && <p className="form-error" role="alert">{error}</p>}
        <Link className="back-link" href="/">← Back to home</Link>
      </div>
      <div className="signin-note">A quiet inbox today. A richer morning tomorrow.</div>
    </main>
  );
}
