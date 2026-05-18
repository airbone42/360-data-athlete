from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SpecialistOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    structure: list[dict] = Field(default_factory=list)
    intervals_icu: str | None = None
    focus: str | None = None
    duration_note: str | None = None
