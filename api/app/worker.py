import asyncio
import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, text

from .config import settings
from .db import SessionLocal, engine
from .models import Briefing, Episode
from .providers import send_episode_email, store_audio, synthesize
from .research import collect_sources, write_script
from .scheduling import next_occurrence

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("daily-context.worker")
MAX_ATTEMPTS = 3
LOCK_ID = 803170241


def claim_due_briefing() -> bool:
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is required")
    now = datetime.now(UTC)
    with SessionLocal() as db, db.begin():
        briefing = db.scalar(
            select(Briefing)
            .where(Briefing.enabled.is_(True), Briefing.next_run_at <= now)
            .order_by(Briefing.next_run_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if briefing is None:
            return False
        scheduled_for = briefing.next_run_at
        briefing.next_run_at = next_occurrence(briefing.schedule_time, briefing.timezone, now)
        db.add(
            Episode(
                briefing_id=briefing.id,
                owner_id=briefing.owner_id,
                owner_email=briefing.owner_email,
                scheduled_for=scheduled_for,
                status="queued",
                available_at=now,
                email_retry_at=now,
            )
        )
        return True


def recover_stale_jobs() -> None:
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is required")
    stale_before = datetime.now(UTC) - timedelta(minutes=25)
    with SessionLocal() as db, db.begin():
        stale = db.scalars(select(Episode).where(Episode.status == "generating", Episode.updated_at < stale_before).with_for_update(skip_locked=True)).all()
        for episode in stale:
            episode.status = "queued" if episode.attempts < MAX_ATTEMPTS else "failed"
            episode.available_at = datetime.now(UTC)
            episode.error_message = "A worker stopped while generating this episode."


def claim_episode() -> UUID | None:
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is required")
    now = datetime.now(UTC)
    with SessionLocal() as db, db.begin():
        episode = db.scalar(
            select(Episode)
            .where(Episode.status == "queued", Episode.available_at <= now, Episode.attempts < MAX_ATTEMPTS)
            .order_by(Episode.available_at, Episode.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if episode is None:
            return None
        episode.status = "generating"
        episode.attempts += 1
        episode.updated_at = now
        return episode.id


async def generate_episode(episode_id: UUID) -> None:
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is required")
    with SessionLocal() as db:
        episode = db.get(Episode, episode_id)
        if episode is None:
            return
        briefing = db.get(Briefing, episode.briefing_id)
        if briefing is None:
            episode.status = "failed"
            episode.error_message = "The briefing was removed before generation."
            db.commit()
            return
        topic, research_window = briefing.topic, briefing.research_window
    try:
        sources = await collect_sources(topic, research_window)
        script = await write_script(topic, research_window, sources)
        audio = await synthesize(script["spoken_script"])
        object_key = f"{episode_id}/episode.mp3"
        await store_audio(object_key, audio)
        with SessionLocal() as db:
            episode = db.get(Episode, episode_id)
            if episode is None:
                return
            episode.title = script["title"]
            episode.summary = script["summary"]
            episode.script = script["script"]
            episode.sources = sources
            episode.duration_seconds = script["duration_seconds"]
            episode.audio_key = object_key
            episode.status = "ready"
            episode.error_message = None
            episode.updated_at = datetime.now(UTC)
            db.commit()
        logger.info("episode_ready id=%s source_count=%s words=%s", episode_id, len(sources), script["word_count"])
    except Exception as exc:
        logger.exception("episode_generation_failed id=%s error_type=%s", episode_id, type(exc).__name__)
        with SessionLocal() as db:
            episode = db.get(Episode, episode_id)
            if episode is None:
                return
            if episode.attempts < MAX_ATTEMPTS:
                episode.status = "queued"
                episode.available_at = datetime.now(UTC) + timedelta(seconds=30 * (2 ** (episode.attempts - 1)))
                episode.error_message = "Generation failed. A retry is scheduled."
            else:
                episode.status = "failed"
                episode.error_message = "Generation could not complete after three attempts."
            episode.updated_at = datetime.now(UTC)
            db.commit()


def claim_notification() -> tuple[UUID, str, str, str] | None:
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is required")
    now = datetime.now(UTC)
    with SessionLocal() as db, db.begin():
        episode = db.scalar(
            select(Episode)
            .where(
                Episode.status == "ready",
                Episode.emailed_at.is_(None),
                Episode.email_attempts < 5,
                Episode.email_retry_at <= now,
            )
            .order_by(Episode.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if episode is None:
            return None
        briefing = db.get(Briefing, episode.briefing_id)
        if briefing is None:
            return None
        episode.email_attempts += 1
        episode.email_retry_at = now + timedelta(minutes=10)
        episode.updated_at = now
        return episode.id, episode.owner_email, episode.title or "Your daily briefing", briefing.topic


async def notify_episode(message: tuple[UUID, str, str, str]) -> None:
    episode_id, email, title, topic = message
    try:
        await send_episode_email(email, title, topic, str(episode_id))
        with SessionLocal() as db:
            episode = db.get(Episode, episode_id)
            if episode is not None:
                episode.emailed_at = datetime.now(UTC)
                episode.email_error = None
                episode.updated_at = datetime.now(UTC)
                db.commit()
    except Exception as exc:
        logger.exception("episode_email_failed id=%s error_type=%s", episode_id, type(exc).__name__)
        with SessionLocal() as db:
            episode = db.get(Episode, episode_id)
            if episode is not None:
                episode.email_error = "Email delivery failed. The episode is available in your account."
                if episode.email_attempts >= 5:
                    episode.email_retry_at = datetime.max.replace(tzinfo=UTC)
                else:
                    episode.email_retry_at = datetime.now(UTC) + timedelta(minutes=10 * episode.email_attempts)
                db.commit()


async def run_worker() -> None:
    if engine is None or SessionLocal is None:
        raise RuntimeError("DATABASE_URL is required")
    required = {
        "SUPABASE_URL": settings.supabase_url,
        "SUPABASE_SERVICE_ROLE_KEY": settings.supabase_service_key,
        "TAVILY_API_KEY": settings.tavily_api_key,
        "GEMINI_API_KEY": settings.gemini_api_key,
        "GNANI_API_KEY": settings.gnani_api_key,
        "RESEND_API_KEY": settings.resend_api_key,
        "EMAIL_FROM": settings.email_from,
        "APP_URL": settings.app_url,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise RuntimeError(f"Worker configuration is missing: {', '.join(missing)}")

    with engine.connect() as lock_connection:
        acquired = bool(lock_connection.execute(text("SELECT pg_try_advisory_lock(:lock_id)"), {"lock_id": LOCK_ID}).scalar())
        lock_connection.commit()
        if not acquired:
            logger.error("Another worker holds the scheduler lock; this worker is stopping")
            return
        logger.info("worker_started poll_seconds=%s", settings.worker_poll_seconds)
        try:
            while True:
                recover_stale_jobs()
                did_work = claim_due_briefing()
                episode_id = claim_episode()
                if episode_id is not None:
                    await generate_episode(episode_id)
                    continue
                notification = claim_notification()
                if notification:
                    await notify_episode(notification)
                    continue
                if not did_work:
                    await asyncio.sleep(settings.worker_poll_seconds)
        finally:
            lock_connection.execute(text("SELECT pg_advisory_unlock(:lock_id)"), {"lock_id": LOCK_ID})


if __name__ == "__main__":
    asyncio.run(run_worker())
