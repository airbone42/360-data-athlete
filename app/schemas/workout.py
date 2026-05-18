from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Import canonical source — schemas mirror, not redefine
from app.graphs.main_daily_planner.workout_parser import VALID_TAGS, VALID_TYPES

WorkoutType = Literal["Run", "Ride", "WeightTraining", "Workout"]
WorkoutEventType = Literal["WORKOUT", "EASY", "LONG", "RACE", "RECOVERY"]


class Exercise(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    sets: int | None = None
    reps: int | None = None
    per_side: bool = False
    weight_kg: float | None = None
    duration_s: int | None = None
    rpe_target: float | None = None
    notes: str | None = None


class WorkoutStep(BaseModel):
    model_config = ConfigDict(extra="ignore")

    step: str
    duration_min: float | None = None
    description: str | None = None
    exercises: list[Exercise] = Field(default_factory=list)


class PlannedWorkout(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    type: str
    name: str
    duration_min: float
    workout_type: str
    tags: list[str] = Field(default_factory=list)
    structure: list[WorkoutStep] = Field(default_factory=list)
    intervals_icu: str | None = None
    intensity: str | None = None
    indoor: bool = False
    description: str | None = None
    duration_range: list[float] | None = None
    coaching_notes: str | None = None

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in VALID_TYPES:
            raise ValueError(f"Invalid type '{v}'. Allowed: {VALID_TYPES}")
        return v

    @field_validator("tags", mode="before")
    @classmethod
    def filter_tags(cls, v: list) -> list:
        return [str(t).lower() for t in v if str(t).lower() in VALID_TAGS]
