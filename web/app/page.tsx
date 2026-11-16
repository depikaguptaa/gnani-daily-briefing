import Link from "next/link";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";

export default async function Home() {
  const supabase = await createClient();
  const { data } = await supabase.auth.getUser();
  if (data.user) redirect("/dashboard");

  return (
    <main className="landing-shell">
      <nav className="landing-nav">
        <Link className="wordmark" href="/">daily<span>context</span></Link>
        <Link className="nav-signin" href="/sign-in">Sign in <span aria-hidden="true">↗</span></Link>
      </nav>
      <section className="hero-grid">
        <div className="hero-copy">
          <p className="eyebrow"><span className="live-dot" /> A clearer start to every day</p>
          <h1>Stay close<br />to what <em>matters.</em></h1>
          <p className="hero-description">Choose a topic. We’ll follow the latest reporting, shape it into a five-minute briefing, and have it waiting when your day begins.</p>
          <Link className="button button-dark" href="/sign-in">Make your first briefing <span aria-hidden="true">→</span></Link>
          <div className="hero-proof"><span className="proof-rule" /> Research linked to its sources, always.</div>
        </div>
        <div className="cover-art" aria-label="A preview of a Daily Context audio briefing">
          <div className="cover-paper">
            <div className="cover-top"><span>DAILY CONTEXT</span><span>NO. 014</span></div>
            <div className="cover-orbit orbit-one" /><div className="cover-orbit orbit-two" />
            <div className="cover-center"><span className="cover-date">MONDAY · 08:00</span><h2>The<br />funding<br /><i>signal.</i></h2><span className="cover-topic">A FIVE-MINUTE BRIEFING<br />ON STARTUP CAPITAL</span></div>
            <div className="cover-wave"><span /><span /><span /><span /><span /><span /><span /><span /><span /><span /><span /><span /><span /><span /><span /><span /><span /><span /><span /><span /><span /><span /><span /><span /><span /><span /><span /><span /><span /><span /><span /><span /><span /><span /><span /><span /><span /><span /><span /><span /><span /><span /></div>
            <div className="cover-footer"><span>RESEARCHED FOR YOU</span><span>05:02</span></div>
          </div>
          <div className="audio-note"><span className="audio-note-icon">♫</span><span><b>Today’s research</b><small>Turned into something you can hear</small></span><span className="audio-note-time">05:02</span></div>
        </div>
      </section>
      <section className="steps-row" aria-label="How it works">
        <div><span>01</span><b>Pick your subject</b><small>Anything you want to keep up with.</small></div>
        <div><span>02</span><b>Choose your moment</b><small>A fresh edition, on your schedule.</small></div>
        <div><span>03</span><b>Press play</b><small>Five minutes, with sources attached.</small></div>
      </section>
      <footer className="landing-footer"><span>DAILY CONTEXT</span><span>Made for the curious, and the short on time.</span></footer>
    </main>
  );
}
