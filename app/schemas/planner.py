from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PlannerOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    coaching_notes: str = ""
    workouts: list[dict] = Field(default_factory=list)
