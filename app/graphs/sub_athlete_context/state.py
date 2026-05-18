from typing import TypedDict


class AthleteContextState(TypedDict):
    athlete_id: str
    date: str
    wellness: dict
    rhr_retry_count: int
    activities: list[dict]
    workouts: list[dict]
    events: list[dict]
    wellness_history: list[dict]
    weather: dict
    weather_warning: bool
    athlete_settings: dict
    context_summary: dict
