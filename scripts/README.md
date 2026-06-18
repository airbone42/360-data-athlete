# `scripts/` — CLI helper inventory

This directory contains the Python helper scripts the plugin agents
invoke under the hood. They are documented here for two audiences:

1. **Plugin users** — you don't normally call these yourself; the
   `aicoach-framework:*` slash commands and sub-agents do that. This
   file exists so you can debug what the system is doing, or invoke a
   step in isolation.
2. **Forks and standalone setups** — if you bypass Claude Code (or run
   the framework against a custom interface), these scripts are the
   programmatic entry points.

All scripts run with `python3 scripts/<name>.py` **from the framework
root** (standalone mode — the primary case this file documents).

When the same scripts are invoked from a slash command or sub-agent
**inside a Claude Code plugin install**, the working directory is the
*consumer's* session root, not the plugin. Plugin commands therefore
spell the path as
`python3 "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/<name>.py` — Claude Code
expands `${CLAUDE_PLUGIN_ROOT}` to the plugin's absolute path before
running the shell, and the bash default `:-.` keeps the same line
working in standalone mode (variable unset → `.` → cwd). If you copy
an invocation from a command/agent file, that's why it has the
prefix; if you copy from this README's table, you're already at the
framework root and the bare form is fine.

Most scripts accept `--help` for the full argument list. Paths resolve
through `app/utils/paths.py` — set `COACH_HOME`, `CONFIG_DIR`,
`DATA_DIR`, `CACHE_DIR` to override the defaults (see `.env.example`).

---

## Context, fetch, push

| Script | Purpose | Typical invocation | Reads | Writes |
|--------|---------|--------------------|-------|--------|
| `fetch_context.py` | Full athlete context (wellness, activities, weather, events, shoes) | `--date YYYY-MM-DD` | intervals.icu API, config | stdout JSON |
| `fetch_type_history.py` | Last N sessions of a given type + activity messages | `--date YYYY-MM-DD --type Run --tags run --max-sessions 5` | intervals.icu API | stdout JSON |
| `fetch_activity.py` | Activity detail + streams + linked planned workout | `--activity-id i12345678` | intervals.icu API | stdout JSON |
| `push_workouts.py` | Push workouts as events to intervals.icu | `echo '<workouts JSON>' \| python3 scripts/push_workouts.py --date YYYY-MM-DD` | stdin, validator | intervals.icu API |
| `delete_workouts.py` | Delete workout events | `--event-ids id1,id2` | — | intervals.icu API |
| `post_message.py` | Post coaching note on an activity, or write a NOTE event on a date | `--activity-id ... --message "..."` or `--date ... --note "..."` | — | intervals.icu API |
| `warmup_cache.py` | Pre-populate the intervals.icu file cache | `--days 30` | intervals.icu API | `cache/` |

## Activity analysis

| Script | Purpose | Typical invocation | Reads | Writes |
|--------|---------|--------------------|-------|--------|
| `download_fit.py` | Download the FIT file for an activity from Garmin | `--date YYYY-MM-DD` | Garmin Connect API | `data/fit/YYYY-MM-DD.fit` |
| `parse_fit.py` | Parse a FIT file → laps + records JSON | `--fit-path data/fit/...` | FIT file | stdout JSON |
| `build_sub_laps.py` | Build sub-lap windows with surface data | `echo '<streams+records JSON>' \| python3 scripts/build_sub_laps.py` | stdin | stdout JSON |
| `extract_run_dynamics.py` | Garmin running dynamics for a video time window | `--activity-id ... --start-s 600 --end-s 720` | FIT file | stdout JSON |
| `analyse_video.py` | Video form check via Gemini (OpenRouter) | `--video <path> --exercise "<name>"` | video file, `OPENROUTER_API_KEY` | stdout markdown |
| `strava_pending.py` | List Strava activities pending title/insights update | `--days 2` or `--activity-id i...` | Strava + intervals.icu APIs | stdout JSON (+ optional intervals.icu rename with `--apply-iv-rename`) |
| `strava_coupling.py` | Same-day Koppeleinheit (ride/legs/double-run) before an activity | `--activity-id i...` | intervals.icu API | stdout JSON |
| `strava_apply.py` | Push title/description to a Strava activity (idempotency safety net) | `--activity-id 12345 --title "..." --description-stdin` | stdin (optional) | Strava API |

## Wellness, HRV, planning

| Script | Purpose | Typical invocation | Reads | Writes |
|--------|---------|--------------------|-------|--------|
| `analyse_hrv_dfa.py` | DFA-α1 coefficient from RR-interval data | `--rr-path data/heartbeat/...` | RR data file | stdout JSON |
| `analyse_dfa_staged.py` | Staged DFA-α1 analysis for a zone-validation protocol | `--rr-path ... --steps ...` | RR data + step protocol | stdout JSON |
| `hrv_readiness.py` | HRV readiness classification (7d-rolling ln-rMSSD vs 60d normal band) | `--date YYYY-MM-DD` | HRV history | stdout JSON |
| `check_heartbeat.py` | Heartbeat sanity check (Polar/H10 sources) | `--rr-path ...` | RR data file | stdout |
| `get_balance_rotation.py` | Daily balance-rotation pick (A/B/C/D) | `--date YYYY-MM-DD [--show]` | `config/balance_pool.json` | stdout JSON / push input |

## Validation

| Script | Purpose | Typical invocation | Reads | Writes |
|--------|---------|--------------------|-------|--------|
| `validate_plan.py` | Mechanical plan validator (rule plug-ins, R001–R011) | `echo '<workouts JSON>' \| python3 scripts/validate_plan.py --date YYYY-MM-DD --json` | stdin, config | stdout JSON (exit 2 on ERROR) |
| `pre_push_validator.py` | Last-line validator wrapper run from `push_workouts.py` | (called internally) | — | — |
| `check_warmup_overlap.py` | Warn on duplicate warmup drills on the same day | `--date YYYY-MM-DD` | intervals.icu API | stdout WARNING lines |
| `audit_consistency.py` | Drift scanner across configs, agents, prompts | `[--offline] > /tmp/audit_raw.json` | configs + intervals.icu NOTEs | stdout JSON |

## Muscle load + nutrition

| Script | Purpose | Typical invocation | Reads | Writes |
|--------|---------|--------------------|-------|--------|
| `log_muscle_load.py` | Log per-muscle load from an activity / backfill | `--activity-id ...` or `--backfill 7 --silent` | activity, `exercise_muscle_mapping.json` | `data/muscles/` |
| `muscle_overview.py` | 30-day muscle fatigue overview, exponential decay | `[--backfill 30] [--review-unmapped]` | `data/muscles/` | stdout table |

## Setup, internals

| Script | Purpose | Typical invocation | Reads | Writes |
|--------|---------|--------------------|-------|--------|
| `strava_auth.py` | One-time Strava OAuth2 flow | `python3 scripts/strava_auth.py` | browser redirect | `.env` (manual) |
| `fetch_shoes.py` | Strava shoes + profile check against `equipment.md` | (no args) | Strava API + config | stdout report |
| `shoe_recommend.py` | Shoe recommendation given today's workouts | `--date YYYY-MM-DD` | shoe state + workouts | stdout JSON |
| `save_feedback.py` | Persist athlete feedback to intervals.icu NOTE | `--date YYYY-MM-DD --note "..."` | — | intervals.icu API |
| `training_flow.py` | End-to-end training flow orchestration (debug / batch) | `--date YYYY-MM-DD` | full context | full plan push |
| `load_prompt.py` | Render a `prompts/*.yaml` template with config substitution (the YAMLs are manually renderable reference prompts; `agents/*.md` are the active definitions) | `--name daily_planner` | `prompts/`, `config/` | stdout |
| `validate_dfa_vs_nolds.py` | Sanity-check internal DFA-α1 against `nolds` reference | (no args) | RR fixture | stdout report |

---

## Notes for external users

- **No keys, no calls.** Most scripts call intervals.icu / Strava / Garmin
  / Gemini. Without the corresponding `.env` keys they will fail at the
  HTTP layer with a clear error.
- **Alex Demo dry run.** `fetch_context.py --date <today>` works without
  any API keys against the bundled `config.example/` demo profile —
  it returns a static context, no live data.
- **Idempotence.** `log_muscle_load.py --backfill`, `strava_apply.py`
  (via the configured footer suffix `INSIGHTS_ANCHOR` — see
  `app/config.py` — and the duplicate-anchor refusal), and
  `push_workouts.py` are idempotent by design. Re-running them does
  not produce duplicates.
- **Exit codes.** `validate_plan.py` exits `2` on a hard ERROR finding;
  `push_workouts.py` propagates that to block the push. Override with
  `--skip-validation` in genuine emergencies (and document why).
