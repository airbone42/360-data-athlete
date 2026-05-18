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
    strava_client_id: str = ""
    strava_client_secret: str = ""
    strava_refresh_token: str = ""
    # Insights-Block on/off toggle for the strava-publisher agent.
    # Default on: every endurance push gets the 2–4 line block + footer.
    # Set `STRAVA_PUBLISHER_FOOTER_ENABLED=false` to opt out — the agent
    # then mirrors only the activity title and skips the insights block
    # entirely (no body lines, no random-gerund footer). Title-only mode
    # is the right setting if you don't want any third-party signature
    # on your Strava feed; note that without the footer there is no
    # idempotency anchor, which is why the whole block is gated.
    strava_publisher_footer_enabled: bool = True
    # Suffix appended after the random gerund in the Strava insights
    # footer. Default carries the project brand `by 360° Data Athlete`
    # so consumer pushes also surface the project in follower feeds —
    # this is intentional public attribution, not a private athlete
    # marker. Override per wrapper via `STRAVA_PUBLISHER_FOOTER_SUFFIX`
    # if you prefer a different signature. The string also doubles as
    # the re-run idempotency anchor (see `strava_pending.py`).
    strava_publisher_footer_suffix: str = "by 360° Data Athlete (https://github.com/airbone42/360-data-athlete/)"
    # OpenRouter `X-Title` header — surfaces on the API account dashboard.
    # Override per wrapper to label requests with the consumer's app name.
    openrouter_x_title: str = "aicoach-framework"

    model_config = {"env_file": _env_file(), "extra": "ignore"}


settings = Settings()
