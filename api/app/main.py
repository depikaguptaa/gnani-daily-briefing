from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import User, current_user
from .config import settings
from .db import get_db
from .models import Briefing, Episode
from .scheduling import next_occurrence, validate_timezone
from .schemas import BriefingCreate, BriefingOut, BriefingPatch, EpisodeList, EpisodeOut
from .providers import delete_audio, load_audio

app = FastAPI(title="Daily Context API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/briefings", response_model=list[BriefingOut])
def list_briefings(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[Briefing]:
    return list(db.scalars(select(Briefing).where(Briefing.owner_id == UUID(user.id)).order_by(Briefing.created_at.desc())))


@app.post("/api/v1/briefings", response_model=BriefingOut, status_code=status.HTTP_201_CREATED)
def create_briefing(payload: BriefingCreate, user: User = Depends(current_user), db: Session = Depends(get_db)) -> Briefing:
    try:
        validate_timezone(payload.timezone)
        next_run = next_occurrence(payload.schedule_time, payload.timezone)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    briefing = Briefing(
        owner_id=UUID(user.id),
        owner_email=user.email,
        topic=payload.topic,
        schedule_time=payload.schedule_time,
        timezone=payload.timezone,
        research_window=payload.research_window,
        enabled=True,
        next_run_at=next_run,
    )
    db.add(briefing)
    db.commit()
    db.refresh(briefing)
    return briefing


@app.patch("/api/v1/briefings/{briefing_id}", response_model=BriefingOut)
def update_briefing(briefing_id: UUID, payload: BriefingPatch, user: User = Depends(current_user), db: Session = Depends(get_db)) -> Briefing:
    briefing = db.scalar(select(Briefing).where(Briefing.id == briefing_id, Briefing.owner_id == UUID(user.id)))
    if briefing is None:
        raise HTTPException(status_code=404, detail="Briefing not found")
    briefing.enabled = payload.enabled
    if payload.enabled:
        briefing.next_run_at = next_occurrence(briefing.schedule_time, briefing.timezone)
    db.commit()
    db.refresh(briefing)
    return briefing


@app.delete("/api/v1/briefings/{briefing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_briefing(briefing_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)) -> Response:
    briefing = db.scalar(select(Briefing).where(Briefing.id == briefing_id, Briefing.owner_id == UUID(user.id)).with_for_update())
    if briefing is None:
        raise HTTPException(status_code=404, detail="Briefing not found")
    episodes = list(db.scalars(select(Episode).where(Episode.briefing_id == briefing.id, Episode.owner_id == UUID(user.id)).with_for_update()))
    if any(episode.status == "generating" for episode in episodes):
        raise HTTPException(status_code=409, detail="Wait for the current episode to finish before deleting this briefing")
    audio_keys = [episode.audio_key for episode in episodes if episode.audio_key]
    try:
        for audio_key in audio_keys:
            if audio_key:
                await delete_audio(audio_key)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Episode storage is temporarily unavailable; the briefing was kept") from exc
    db.delete(briefing)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/api/v1/episodes", response_model=EpisodeList)
def list_episodes(user: User = Depends(current_user), db: Session = Depends(get_db)) -> EpisodeList:
    rows = db.execute(
        select(Episode, Briefing.topic)
        .join(Briefing, Briefing.id == Episode.briefing_id)
        .where(Episode.owner_id == UUID(user.id), Briefing.owner_id == UUID(user.id))
        .order_by(Episode.scheduled_for.desc())
        .limit(50)
    ).all()
    items = [
        EpisodeOut(
            id=episode.id,
            briefing_id=episode.briefing_id,
            topic=topic,
            status=episode.status,
            title=episode.title,
            summary=episode.summary,
            scheduled_for=episode.scheduled_for,
            duration_seconds=episode.duration_seconds,
            script=episode.script,
            sources=episode.sources,
            error_message=episode.error_message,
        )
        for episode, topic in rows
    ]
    return EpisodeList(items=items)


@app.get("/api/v1/episodes/{episode_id}/audio")
async def episode_audio(episode_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)) -> Response:
    episode = db.scalar(select(Episode).where(Episode.id == episode_id, Episode.owner_id == UUID(user.id)))
    if episode is None or episode.status != "ready" or not episode.audio_key:
        raise HTTPException(status_code=404, detail="Episode not found")
    try:
        data = await load_audio(episode.audio_key)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Episode audio is temporarily unavailable") from exc
    return Response(content=data, media_type="audio/mpeg", headers={"Cache-Control": "private, no-store"})
