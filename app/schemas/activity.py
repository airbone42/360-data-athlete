from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Activity(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str | None = None
    name: str | None = None
    type: str | None = None
    start_date_local: str | None = None
    moving_time: int | None = None
    workout_type: str | None = None
    tags: list[str] = Field(default_factory=list)
    icu_training_load: float | None = None
    icu_hr_zone_times: list[float] = Field(default_factory=list)
    gear_id: str | None = None
    icu_gear_id: str | None = None
    event_description: str | None = None
    paired_event_id: str | None = None
