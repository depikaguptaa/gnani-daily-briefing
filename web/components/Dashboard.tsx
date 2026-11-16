"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, apiBlob } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";

type Briefing = {
  id: string;
  topic: string;
  schedule_time: string;
  timezone: string;
  research_window: "day" | "week" | "month";
  enabled: boolean;
  next_run_at: string;
};
type Source = { id: string; title: string; url: string; publisher: string; published_at?: string | null };
type Episode = {
  id: string;
  briefing_id: string;
  topic: string;
  status: "queued" | "generating" | "ready" | "failed";
  title: string | null;
  summary: string | null;
  scheduled_for: string;
  duration_seconds: number | null;
  script: string | null;
  sources: Source[];
  error_message: string | null;
};

const windowNames = { day: "24 hours", week: "7 days", month: "30 days" };

function formatDate(value: string, timezone: string) {
  return new Intl.DateTimeFormat(undefined, { weekday: "long", month: "long", day: "numeric", timeZone: timezone }).format(new Date(value));
}
function formatDuration(seconds?: number | null) {
  if (!seconds) return "about 5 min";
  const minutes = Math.floor(seconds / 60);
  const remaining = seconds % 60;
  return `${minutes}:${String(remaining).padStart(2, "0")}`;
}

export default function Dashboard({ email }: { email: string }) {
  const router = useRouter();
  const [briefings, setBriefings] = useState<Briefing[]>([]);
  const [episodes, setEpisodes] = useState<Episode[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [topic, setTopic] = useState("");
  const [scheduleTime, setScheduleTime] = useState("08:00");
  const [timezone, setTimezone] = useState("Asia/Kolkata");
  const [researchWindow, setResearchWindow] = useState<"day" | "week" | "month">("day");
  const [audioUrls, setAudioUrls] = useState<Record<string, string>>({});
  const [loadingAudio, setLoadingAudio] = useState<string | null>(null);
  const [focusedEpisode, setFocusedEpisode] = useState<string | null>(null);
  const [today, setToday] = useState("");
  const audioUrlsRef = useRef(audioUrls);

  const load = useCallback(async () => {
    setError("");
    try {
      const [briefingList, episodeList] = await Promise.all([
        api<Briefing[]>("/api/v1/briefings"),
        api<{ items: Episode[] }>("/api/v1/episodes"),
      ]);
      setBriefings(briefingList);
      setEpisodes(episodeList.items);
      const target = new URLSearchParams(window.location.search).get("episode");
      if (target) setFocusedEpisode(target);
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : "Could not load your briefings.";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const browserTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    setToday(new Intl.DateTimeFormat(undefined, { weekday: "long", month: "long", day: "numeric" }).format(new Date()).toUpperCase());
    if (browserTimezone) setTimezone(browserTimezone);
    void load();
  }, [load]);

  useEffect(() => {
    audioUrlsRef.current = audioUrls;
  }, [audioUrls]);

  useEffect(() => () => Object.values(audioUrlsRef.current).forEach((url) => URL.revokeObjectURL(url)), []);

  useEffect(() => {
    if (!focusedEpisode || loading) return;
    document.getElementById(`episode-${focusedEpisode}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [episodes, focusedEpisode, loading]);

  const readyCount = useMemo(() => episodes.filter((episode) => episode.status === "ready").length, [episodes]);

  async function createBriefing(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      await api<Briefing>("/api/v1/briefings", {
        method: "POST",
        body: JSON.stringify({ topic: topic.trim(), schedule_time: scheduleTime, timezone, research_window: researchWindow }),
      });
      setTopic("");
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Your briefing could not be saved.");
    } finally {
      setSaving(false);
    }
  }

  async function toggleBriefing(briefing: Briefing) {
    setError("");
    try {
      await api<Briefing>(`/api/v1/briefings/${briefing.id}`, {
        method: "PATCH",
        body: JSON.stringify({ enabled: !briefing.enabled }),
      });
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The schedule could not be updated.");
    }
  }

  async function removeBriefing(briefing: Briefing) {
    if (!window.confirm("Delete this briefing and its episode history?")) return;
    setError("");
    try {
      await api<void>(`/api/v1/briefings/${briefing.id}`, { method: "DELETE" });
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The briefing could not be deleted.");
    }
  }

  async function listen(episode: Episode) {
    if (audioUrls[episode.id]) return;
    setLoadingAudio(episode.id);
    setError("");
    try {
      const blob = await apiBlob(`/api/v1/episodes/${episode.id}/audio`);
      const url = URL.createObjectURL(blob);
      setAudioUrls((current) => ({ ...current, [episode.id]: url }));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Audio could not be loaded.");
    } finally {
      setLoadingAudio(null);
    }
  }

  async function signOut() {
    await createClient().auth.signOut();
    router.push("/");
    router.refresh();
  }

  return (
    <main className="dashboard-shell">
      <aside className="dashboard-rail">
        <Link className="wordmark" href="/">daily<span>context</span></Link>
        <div className="rail-label">YOUR SPACE</div>
        <a className="rail-link active" href="#overview"><span className="rail-icon">◷</span> Overview</a>
        <a className="rail-link" href="#briefings"><span className="rail-icon">＋</span> Briefings</a>
        <a className="rail-link" href="#episodes"><span className="rail-icon">♫</span> Episodes <span className="rail-count">{readyCount}</span></a>
        <div className="rail-bottom"><span className="avatar-mark">{email.slice(0, 1).toUpperCase()}</span><div className="rail-user"><b>{email}</b><button onClick={signOut}>Sign out</button></div></div>
      </aside>

      <section className="dashboard-main" id="overview">
        <header className="dashboard-top"><span>{today || "YOUR DAILY DESK"}</span><span className="top-timezone">{timezone.replaceAll("_", " ")}</span></header>
        <div className="dashboard-heading"><div><p className="eyebrow">YOUR PERSONAL AUDIO DESK</p><h1>A little more in the know.</h1><p>Research on your terms, ready when you are.</p></div><div className="desk-mark"><span>◉</span><small>YOUR<br />EDITION</small></div></div>

        {error && <div className="notice-error" role="alert"><span>{error}</span><button onClick={() => setError("")} aria-label="Dismiss">×</button></div>}

        <div className="dashboard-columns">
          <div className="main-column">
            <section className="section-block" id="briefings">
              <div className="section-title"><div><p className="eyebrow">ON YOUR SCHEDULE</p><h2>Your briefings</h2></div><span className="section-count">{briefings.length} {briefings.length === 1 ? "topic" : "topics"}</span></div>
              {loading ? <div className="loading-line">Gathering your desk…</div> : briefings.length === 0 ? <div className="empty-briefings"><span className="empty-star">✳</span><div><b>Your daily lineup starts here.</b><p>Add a topic and choose when you’d like to hear about it.</p></div></div> : <div className="briefing-list">{briefings.map((briefing, index) => (
                <article className={`briefing-card ${briefing.enabled ? "" : "paused"}`} key={briefing.id}>
                  <span className={`briefing-index index-${index % 3}`}>{String(index + 1).padStart(2, "0")}</span>
                  <div className="briefing-content"><h3>{briefing.topic}</h3><div className="briefing-meta"><span>{briefing.schedule_time.slice(0, 5)}</span><span className="meta-dot">·</span><span>{briefing.timezone.replaceAll("_", " ")}</span><span className="meta-dot">·</span><span>Last {windowNames[briefing.research_window]}</span></div></div>
                  <div className="briefing-actions"><button className={`schedule-toggle ${briefing.enabled ? "is-on" : ""}`} onClick={() => void toggleBriefing(briefing)} aria-label={briefing.enabled ? "Pause briefing" : "Resume briefing"} aria-pressed={briefing.enabled}><span /></button><button className="icon-button remove-button" onClick={() => void removeBriefing(briefing)} aria-label={`Delete ${briefing.topic}`}>×</button></div>
                </article>
              ))}</div>}
            </section>

            <section className="section-block episode-section" id="episodes">
              <div className="section-title"><div><p className="eyebrow">THE LISTENING ROOM</p><h2>Recent episodes</h2></div><span className="section-count">{episodes.length} editions</span></div>
              {loading ? <div className="loading-line">Loading episodes…</div> : episodes.length === 0 ? <div className="empty-episodes"><div className="empty-record">♫</div><div><b>Your first episode will appear here.</b><p>Once your briefing runs, we’ll email you a private listening link.</p></div></div> : <div className="episode-list">{episodes.map((episode) => (
                <article id={`episode-${episode.id}`} className={`episode-card ${focusedEpisode === episode.id ? "is-focused" : ""}`} key={episode.id}>
                  <div className="episode-card-head"><div className="episode-cover"><span className="cover-small-lines"><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /></span></div><div className="episode-main"><div className="episode-date">{formatDate(episode.scheduled_for, briefings.find((item) => item.id === episode.briefing_id)?.timezone ?? timezone)}</div><h3>{episode.title ?? episode.topic}</h3><p>{episode.summary ?? episode.topic}</p><div className="episode-tags"><span>{episode.status === "ready" ? "READY TO LISTEN" : episode.status === "failed" ? "NEEDS ATTENTION" : "IN THE WORKS"}</span><span>·</span><span>{episode.status === "ready" ? formatDuration(episode.duration_seconds) : episode.status === "failed" ? "Retry limit reached" : "Researching sources"}</span></div></div>
                    {episode.status === "ready" && !audioUrls[episode.id] && <button className="play-button" onClick={() => void listen(episode)} disabled={loadingAudio === episode.id} aria-label={`Load audio for ${episode.title ?? episode.topic}`}>{loadingAudio === episode.id ? "…" : "▶"}</button>}
                  </div>
                  {episode.status === "ready" && audioUrls[episode.id] && <audio className="episode-audio" controls preload="none" src={audioUrls[episode.id]} />}
                  {episode.status === "failed" && <p className="episode-error">{episode.error_message ?? "This episode could not be created."}</p>}
                  {episode.status === "ready" && <details className="episode-details"><summary>Read the script and sources <span>↗</span></summary><div className="episode-script">{episode.script}</div>{episode.sources.length > 0 && <ol className="source-list">{episode.sources.map((source) => <li key={source.id}><span>{source.id}</span><a href={source.url} target="_blank" rel="noreferrer">{source.title}</a><small>{source.publisher}{source.published_at ? ` · ${source.published_at}` : ""}</small></li>)}</ol>}</details>}
                </article>
              ))}</div>}
            </section>
          </div>

          <aside className="create-panel">
            <div className="create-panel-head"><div className="create-icon">＋</div><p className="eyebrow">A NEW THREAD TO FOLLOW</p><h2>Make it yours.</h2><p>What would you like to know more about?</p></div>
            <form onSubmit={createBriefing} className="briefing-form">
              <label htmlFor="topic">Your research topic</label>
              <textarea id="topic" required minLength={8} maxLength={500} rows={4} value={topic} onChange={(event) => setTopic(event.target.value)} placeholder="e.g. Startup funding announced in India" />
              <div className="field-row"><div className="field-half"><label htmlFor="schedule-time">Every day at</label><input id="schedule-time" type="time" required value={scheduleTime} onChange={(event) => setScheduleTime(event.target.value)} /></div><div className="field-half"><label htmlFor="research-window">Research from</label><select id="research-window" value={researchWindow} onChange={(event) => setResearchWindow(event.target.value as "day" | "week" | "month")}><option value="day">Last 24 hours</option><option value="week">Last 7 days</option><option value="month">Last 30 days</option></select></div></div>
              <label htmlFor="timezone">Time zone</label><input id="timezone" value={timezone} onChange={(event) => setTimezone(event.target.value)} required maxLength={80} />
              <p className="timezone-help">Use an IANA name, like Asia/Kolkata or America/New_York.</p>
              <button className="button button-dark create-submit" disabled={saving}>{saving ? "Setting up your briefing…" : "Add to my daily lineup"}<span aria-hidden="true">→</span></button>
            </form>
            <div className="create-footnote"><span>✳</span><p>Every edition links back to the reporting behind it.</p></div>
          </aside>
        </div>
        <footer className="dashboard-footer"><span>DAILY CONTEXT · PRIVATE BY DESIGN</span><button onClick={() => void load()}>Refresh desk ↻</button></footer>
      </section>
    </main>
  );
}
