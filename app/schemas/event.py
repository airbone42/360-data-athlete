from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

EventCategory = Literal["WORKOUT", "RACE_A", "RACE_B", "RACE_C", "NOTE"]


class Event(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: int | str | None = None
    uid: str | None = None
    category: EventCategory | None = None
    start_date_local: str | None = None
    name: str | None = None
    description: str | None = None
