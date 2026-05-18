from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ContextDict(BaseModel):
    """Validated output of build_context(). Protects the camelCase contract."""
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    hrv_context: Any = Field(None, alias="hrvContext")
    hrv: Any = None
    rhr: Any = None
    sleep: Any = None
    sleep_hours: Any = Field(None, alias="sleepHours")
    activities: list[dict] = Field(default_factory=list)
    ctl: Any = None
    atl: Any = None
    tsb: Any = None
    ctl_display: Any = Field(None, alias="ctlDisplay")
    hrv_baseline: Any = Field(None, alias="hrvBaseline")
    hrv_deviation: Any = Field(None, alias="hrvDeviation")
    sleep_trend: Any = Field(None, alias="sleepTrend")
    rhr_trend: Any = Field(None, alias="rhrTrend")
    ctl_trend: Any = Field(None, alias="ctlTrend")
    cycle_hint: Any = Field(None, alias="cycleHint")
    zone_distribution: Any = Field(None, alias="zoneDistribution")
    weekly_zone_balance: Any = Field(None, alias="weeklyZoneBalance")
    weekly_hard_reize_balance: Any = Field(None, alias="weeklyHardReizeBalance")
    meso_load_trend: Any = Field(None, alias="mesoLoadTrend")
    weather_info: Any = Field(None, alias="weatherInfo")
    intensity_readiness: Any = Field(None, alias="intensityReadiness")
    days_since_intense: Any = Field(None, alias="daysSinceIntense")
    last_rest_day: Any = Field(None, alias="lastRestDay")
    athlete_feedback: Any = Field(None, alias="athleteFeedback")
    event_list: Any = Field(None, alias="eventList")
    race_in_days: Any = Field(None, alias="raceInDays")
    date_str: Any = Field(None, alias="dateStr")
    hr_zones: Any = Field(None, alias="hrZones")
    hrv_review_pending: Any = Field(None, alias="hrvReviewPending")
    skipped_workouts: list[Any] = Field(default_factory=list, alias="skippedWorkouts")
    data_warnings: list[Any] = Field(default_factory=list, alias="dataWarnings")
