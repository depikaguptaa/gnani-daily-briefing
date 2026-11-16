from datetime import datetime, time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class BriefingCreate(BaseModel):
    topic: str = Field(min_length=8, max_length=500)
    schedule_time: time
    timezone: str = Field(min_length=1, max_length=80)
    research_window: Literal["day", "week", "month"] = "day"

    @field_validator("topic")
    @classmethod
    def trim_topic(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 8:
            raise ValueError("Add a little more detail to your research topic")
        return cleaned

    @field_validator("schedule_time")
    @classmethod
    def local_time_only(cls, value: time) -> time:
        if value.tzinfo is not None:
            raise ValueError("Set the time separately from its timezone")
        return value


class BriefingPatch(BaseModel):
    enabled: bool


class BriefingOut(BaseModel):
    id: UUID
    topic: str
    schedule_time: time
    timezone: str
    research_window: str
    enabled: bool
    next_run_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class EpisodeOut(BaseModel):
    id: UUID
    briefing_id: UUID
    topic: str
    status: str
    title: str | None
    summary: str | None
    scheduled_for: datetime
    duration_seconds: int | None
    script: str | None
    sources: list[dict]
    error_message: str | None


class EpisodeList(BaseModel):
    items: list[EpisodeOut]
