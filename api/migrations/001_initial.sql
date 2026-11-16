CREATE TABLE IF NOT EXISTS briefings (
    id uuid PRIMARY KEY,
    owner_id uuid NOT NULL,
    owner_email varchar(320) NOT NULL,
    topic text NOT NULL,
    schedule_time time NOT NULL,
    timezone varchar(80) NOT NULL,
    research_window varchar(16) NOT NULL DEFAULT 'day' CHECK (research_window IN ('day', 'week', 'month')),
    enabled boolean NOT NULL DEFAULT true,
    next_run_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_briefings_owner_id ON briefings(owner_id);
CREATE INDEX IF NOT EXISTS ix_briefings_next_run_at ON briefings(next_run_at) WHERE enabled = true;

CREATE TABLE IF NOT EXISTS episodes (
    id uuid PRIMARY KEY,
    briefing_id uuid NOT NULL REFERENCES briefings(id) ON DELETE CASCADE,
    owner_id uuid NOT NULL,
    owner_email varchar(320) NOT NULL,
    scheduled_for timestamptz NOT NULL,
    status varchar(16) NOT NULL CHECK (status IN ('queued', 'generating', 'ready', 'failed')),
    title varchar(180),
    summary varchar(320),
    script text,
    sources jsonb NOT NULL DEFAULT '[]'::jsonb,
    audio_key varchar(512),
    duration_seconds integer,
    attempts integer NOT NULL DEFAULT 0,
    available_at timestamptz NOT NULL DEFAULT now(),
    error_message text,
    emailed_at timestamptz,
    email_attempts integer NOT NULL DEFAULT 0,
    email_retry_at timestamptz NOT NULL DEFAULT now(),
    email_error text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_episode_briefing_schedule UNIQUE (briefing_id, scheduled_for)
);
CREATE INDEX IF NOT EXISTS ix_episodes_owner_id ON episodes(owner_id);
CREATE INDEX IF NOT EXISTS ix_episodes_status_available ON episodes(status, available_at);
CREATE INDEX IF NOT EXISTS ix_episodes_notification_retry ON episodes(status, emailed_at, email_retry_at);

-- These tables are accessed only by the trusted FastAPI and worker processes.
-- Frontend users do not get direct Supabase Data API privileges for them.
ALTER TABLE briefings ENABLE ROW LEVEL SECURITY;
ALTER TABLE episodes ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE briefings, episodes FROM PUBLIC, anon, authenticated;
GRANT ALL ON TABLE briefings, episodes TO service_role;
