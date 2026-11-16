import uuid
from datetime import datetime, time

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Time, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Briefing(Base):
    __tablename__ = "briefings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    owner_email: Mapped[str] = mapped_column(String(320), nullable=False)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    schedule_time: Mapped[time] = mapped_column(Time, nullable=False)
    timezone: Mapped[str] = mapped_column(String(80), nullable=False)
    research_window: Mapped[str] = mapped_column(String(16), nullable=False, default="day")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Episode(Base):
    __tablename__ = "episodes"
    __table_args__ = (UniqueConstraint("briefing_id", "scheduled_for", name="uq_episode_briefing_schedule"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    briefing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("briefings.id", ondelete="CASCADE"), nullable=False, index=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    owner_email: Mapped[str] = mapped_column(String(320), nullable=False)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued", index=True)
    title: Mapped[str | None] = mapped_column(String(180))
    summary: Mapped[str | None] = mapped_column(String(320))
    script: Mapped[str | None] = mapped_column(Text)
    sources: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)
    audio_key: Mapped[str | None] = mapped_column(String(512))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    error_message: Mapped[str | None] = mapped_column(Text)
    emailed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    email_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    email_retry_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    email_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
