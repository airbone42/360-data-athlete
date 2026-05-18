from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Wellness(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str | None = None
    hrv: float | None = None
    resting_hr: int | None = Field(None, alias="restingHR")
    sleep_score: float | None = Field(None, alias="sleepScore")
    sleep_secs: int | None = Field(None, alias="sleepSecs")
    ctl: float | None = None
    atl: float | None = None
