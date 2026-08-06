from pathlib import Path

from pydantic_settings import BaseSettings

from app.utils.paths import COACH_HOME, FRAMEWORK_ROOT


def _env_file() -> str:
    """Prefer .env in COACH_HOME (private wrapper), fall back to framework root."""
    primary = COACH_HOME / ".env"
    if primary.exists():
        return str(primary)
    return str(FRAMEWORK_ROOT / ".env")


class Settings(BaseSettings):
    openrouter_api_key: str = ""
    telegram_bot_access_token: str = ""
    telegram_allowed_user_ids: str = ""
    intervals_icu_api_key: str = ""
    intervals_icu_athlete_id: str = ""
    redis_url: str = "redis://redis:6379"
    langchain_tracing_v2: bool = True
    langchain_api_key: str = ""
    langchain_project: str = "ai_coach_dev"
    telegram_chat_id: str = ""
    openrouter_model: str = "google/gemini-3.1-pro-preview"
    gemini_model: str = "google/gemini-2.0-flash-001"
    garmin_email: str = ""
    garmin_password: str = ""
    # Source of truth for shoe data (gear list, mileage, active/retired,
    # last-used rotation) feeding the shoe advisor.
    #   intervals (default) — read native intervals.icu gear; mileage is
    #     accumulated by intervals.icu itself from each activity's gear_id.
    #     The coach sets the recommended shoe on the finished activity
    #     (see scripts/set_activity_gear.py).
    #   off — shoe advisor disabled (empty shoe list).
    shoe_tracking_backend: str = "intervals"
    # Whether a shoe already attached to a finished activity by the recording
    # device / import counts as a real assignment.
    #   false (default) — it does. `set_activity_gear.py` leaves an activity
    #     alone when it already carries an *active* Shoes-type gear, on the
    #     assumption the athlete (or their device) maintains that field. Only
    #     a retired / non-shoe "phantom" id is overwritten.
    #   true — it does not. The coach's recommendation always wins and the
    #     device value is overwritten, whether it is active or retired.
    # Set this to true when the athlete does not maintain shoes on the
    # watch: many devices stamp a default shoe onto every imported run, and
    # while it stays *active* the default guard preserves it, so the coach
    # pick is silently dropped and the rotation mileage accrues to the wrong
    # shoe. `--force` remains the per-call override in either mode; an
    # explicit `--gear-id` is unaffected.
    shoe_ignore_device_gear: bool = False
    # OpenRouter `X-Title` header — surfaces on the API account dashboard.
    # Override per wrapper to label requests with the consumer's app name.
    openrouter_x_title: str = "aicoach-framework"

    model_config = {"env_file": _env_file(), "extra": "ignore"}


settings = Settings()
