# 360° Data Athlete

> ⚠️ **Experimental project. Not intended for unsupervised training.**
>
> This is a coding experiment with multi-agent systems, using sport
> training as the problem domain. It does **not** replace a coach or
> sports-medical advice. Use only with a solid training background, at
> your own risk. No warranty, no support, no audit.

An **AI coach for endurance and strength athletes**, distributed as a
[Claude Code](https://claude.com/claude-code) plugin. A team of
specialised sub-agents (planner, three workout specialists, mental
coach, video analyst, post-activity analyst, data scientist, plan
validator, config auditor, two clinical consultants) collaborate to
plan, push, and review training — grounded in intervals.icu, Strava,
Garmin and (optionally) Telegram.

### Framing

This is not a multi-agent example. For pure multi-agent orchestration
there are better-fitting frameworks (LangChain / LangGraph, AutoGen,
CrewAI). What this project explores is something else: **Claude Code as
a general-purpose agent harness, applied to a domain that isn't code.**

Claude Code is usually marketed for software engineering — but it
already ships everything you need to drive a long-running, file-backed,
sub-agent-orchestrating workflow against a real-world domain: namespaced
sub-agents with isolated context, slash commands, hooks, MCP servers,
plugins, persistent state in plain files, terminal + Telegram surfaces.
Training planning is the test bench: it has conflicting constraints
(HRV vs. schedule, injury vs. progression, weather vs. pillar rotation),
persistent state across days, and an actual human (the maintainer) who
pushes back when the system gets it wrong. Every rule in the framework
exists because at some point that pushback exposed a gap.

If you came for the agent design, the
[architecture doc](docs/architecture.md), `agents/*.md`, and
`framework/CLAUDE.md` are the interesting parts. If you came for
training: read on.

---

## What it does

- **Daily planning** that respects HRV, CTL / ATL / TSB, sleep, weather,
  races on the calendar, and active injury restrictions
- **Specialist delegation** — each workout type has its own pane with the
  right context (type history, exercise progressions, validator rules)
- **Pre-push validation** — mechanical (`scripts/validate_plan.py`,
  rule-based) and semantic (`plan-validator` subagent)
- **Post-activity analysis** — factual lap chronicle + coaching feedback,
  HRV-response review
- **Video form check** via Gemini for strength / core / ninja and running
- **Per-muscle load tracking** with a 30-day fatigue overview
- **Consistency audit** that scans for drift across configs, agents,
  prompts — with the exercise-log slice auto-surfaced at every session
  start, so stale progression entries don't wait for `/audit` to be
  noticed
- **Optional Telegram channel** for use away from the terminal

---

## How the daily planning works

The `/training` command is the central workflow — this is what actually
runs when an athlete says "plan today". The flow is deliberately
multi-stage so each stage has the right context and nothing else.

```
fetch_context  →  planner  →  specialists (per workout)
                                    ↓
                            cross-workout review
                                    ↓
                  mechanical validator + semantic plan-validator
                                    ↓
                            present to athlete
                                    ↓
                    accept  →  push to intervals.icu
```

### 1. Context (`fetch_context.py`)

A single Python entry point pulls everything the planner needs and
normalises it into one JSON blob:

- Wellness: HRV, baseline, deviation, RHR, sleep score + hours, CTL, ATL,
  TSB, CTL trend, weekly load history
- Activity history (4 weeks), zone distribution, weekly polarisation
- Upcoming events / race-in-days from intervals.icu calendar
- Athlete feedback NOTEs (last 4 weeks)
- Active injury / pillar / muscle blocks from `athlete_static.md` +
  recovery rules
- HR zones from intervals.icu settings (read 1:1, never reconstructed)
- Weather forecast for the planning day
- Shoe fleet + recommendation (when Run is on the plan)
- **HRV-forecast verdict** for yesterday's training response (see below)

The athlete config in `config/*.md` is merged over the framework defaults
in `config.example/*.md`, so each athlete sees their own zones,
priorities, restrictions, and language.

### 2. HRV readiness — why it matters

A naive HRV-gated coach reads "HRV below normal → block intensity". That
works on rest days but fails the day after a hard session: HRV *should*
drop after Z4 intervals — that's the autonomic nervous system doing its
job. Without context the coach downgrades the planned session needlessly
(silent over-conservatism).

The framework used to try to *predict* tomorrow's HRV from today's
training load (a personal regression). An out-of-sample test on real data
showed that, for a single-input daily model, training load has **no
reliable predictive value** for next-morning HRV — day-to-day HRV is
dominated by sleep, stress, alcohol, and measurement noise, not by load.
The literature agrees: no established protocol forecasts HRV from load;
they all compare the *current* HRV against a personal normal range. (See
[research/hrv-prediction-vs-readiness-modeling.md](research/hrv-prediction-vs-readiness-modeling.md).)

So the coach now runs a **readiness check** instead of a forecast. Rather
than reacting to a single noisy daily value, it tracks the **7-day average
of ln-rMSSD** (a smoothed HRV measure) and asks whether it sits inside the
athlete's **personal normal range** — a band built from the last 60 days
(mean ± 0.5·SD), in the spirit of "normal is good", not "higher is
better". One bad day is noise; several days in a row below the band is a
real fatigue signal (`hrv_readiness.py`).

| Where the 7-day average sits | Verdict | Coach reaction |
|------------------------------|---------|----------------|
| Inside the normal band | `clear` | Planned stimulus proceeds — no HRV downgrade |
| Above the band | `above` | Good recovery/adaptation — a small bump is fine if other signals agree |
| Below the band 1–2 days | `watch` | Soft signal — proceed but note it; ask about external factors |
| Below the band 3+ days | `hold` | Hard signal — recovery is the default (aligns with the combined HRV+RHR overload trigger) |
| < 30 valid days in the window | `insufficient_data` | Fall back to the simple 90-day-median rule until the reference fills in |

The current verdict is a top-level field (`hrvReadiness`) in the context —
the planner reads it like `intensityReadiness`, no separate script call. A
🔴 readiness signal paired with verdict `clear` no longer silently triggers
a deload; it's a flag, not a stop. An advisory `hrvCvTrend` field also
reports whether day-to-day HRV is getting more erratic (an early warning)
without gating anything by itself.

### 3. Planner

The `planner` sub-agent runs in its own pane with the full context and
all athlete configs available. Its job is **what to train**, not how:

- Decide today's session count (single, double, rest)
- Pick the type / pillar for each session (Run, Ride, ninja Pull, etc.)
- Set duration / duration range, target intensity (Z1–Z5 or RPE band)
- Note hard exclusions ("no L-Sit today", "Achilles caution: no plyo")
- Flag context that the specialists need (HRV verdict, taper window,
  weather forcing indoor, sibling-workout volume cap)

The planner never names exercises, sets, reps, or watts. Those are
specialist concerns.

A few gates that fire here:

- **Deload gate** (`mesoLoadTrend`): looks at 4 rolling 7-day load
  windows, athlete-specific CTL threshold (default 24, override per
  athlete in `athlete_status.md` → `deload_ctl_threshold`), and rebuild
  patterns. Suggests "deload recommended" only when *all* three gates
  pass — otherwise the planner stays in build phase.
- **Taper window**: read from `competition_plan.md`. The planner knows
  whether the next race is inside its taper window or still in the
  build phase, and ignores generic deload suggestions accordingly.
- **Recovery week active**: a recovery week is committed for 7 days
  once started; the planner doesn't re-evaluate daily.

### 4. Specialists

Per workout, the planner directive goes to one of three specialists in
sequence (complementary → ninja → endurance, so the strength baseline
sets the muscle context for the others):

- `specialist-endurance` — Run / Ride. Reads exercise log + zone targets
  + intervals.icu formatting rules. Outputs structure + `intervals_icu`
  field (Garmin-syncable workout text) + surface (asphalt / forest path
  / trail / track / treadmill, used by the shoe advisor).
- `specialist-complementary` — Strength / plyo / core. Reads
  `exercise_progressions.md` (per-exercise load / rep / RPE history) +
  type history and picks the next progression step itself.
- `specialist-ninja` — Ninja athletics (Grip / Pull / Push / Core /
  Explosive Power). Rotates pillars; the rotation cadence and current
  history come from the context.

Each specialist reads the prior specialists' output as sibling context —
so the ninja agent knows what the strength agent put in, and the
endurance agent sees both before designing the run. This is where
warm-up de-duplication, muscle-group conflict detection, and volume
caps actually happen.

### 5. Validation

Two layers, mandatory before any push:

- **Mechanical** (`validate_plan.py`, rule-based plugin set): reps cap,
  shoulder blocks, surface field, glute DOMS, achilles + plyo +
  asphalt, LTHR drift, pillar duplication, %LTHR plausibility, distance
  format. Findings come back as ERROR / WARNING / INFO. ERRORs block.
- **Semantic** (`plan-validator` sub-agent, fresh context): pillar
  rotation, stimulus adequacy vs. wellness, weekly volume jumps,
  progression consistency against `exercise_progressions.md`, form
  findings from `exercise_log.md`.

Both run before the plan is shown to the athlete, not after.

### 6. Presentation, accept, push

The plan is presented as readable markdown with one rationale sentence
per session. The coach proposes **one** plan — no menu, no
options-list. The athlete accepts (`ok`, `passt`, `go`, …) or pushes
back; pushback re-enters the relevant pane. On accept, `push_workouts.py`
serialises the workouts to intervals.icu (one event per workout, plus
the daily balance-rotation unit). Once Strava picks the activities up,
the `strava-publisher` agent (`/strava`) mirrors the names and adds a
follower-facing insights block on endurance activities — invoked
automatically as step 6.6 of `/analyse`, or manually any time.

The insights block (2–4 lines of curated form/HR/pace insight plus a
short footer) is **on by default** — Run / VirtualRun / Ride /
VirtualRide activities get enriched on every push.

The footer is the last line of the block and looks like:

```
Pondering by 360° Data Athlete
```

The leading word is a **random gerund** drawn fresh per push from a
small wordlist ([`app/data/gerunds.json`](app/data/gerunds.json) —
inspired by the Claude-Code CLI spinner vocabulary; *Beaming*,
*Booping*, *Razzmatazzing*, ~250 entries). The suffix after it is a
fixed string and doubles as the re-run idempotency anchor —
`strava_pending.py` matches it literally to skip activities that have
already been enriched.

Three ENV variables control this, all in [`.env.example`](.env.example):

- **`STRAVA_PUBLISH_ENABLED`** (default `false`) — master on/off switch
  for the whole Strava title/insights sync. It ships **off** because
  Strava has moved activity writes behind its updated developer-program
  access: `PUT /activities/{id}` returns **403 Forbidden** for apps
  without the `activity:write` scope (this is independent of your
  personal Strava subscription). While disabled, `/strava` and
  `/analyse` step 6.6 short-circuit cleanly — `strava_apply.py` skips
  the write as a no-op and `strava_pending.py` reports nothing pending,
  so no Strava call is made and no 403 surfaces. Set it to `true` only
  once your Strava app actually holds write access.
- **`STRAVA_PUBLISHER_FOOTER_ENABLED`** (default `true`) — set to
  `false` to opt out entirely. The agent then mirrors the title only
  and leaves the description untouched; no body lines, no footer.
- **`STRAVA_PUBLISHER_FOOTER_SUFFIX`** (default `by 360° Data Athlete`) —
  override the fixed suffix. The default carries the project name on
  purpose — light open-source attribution surfacing in the follower's
  feed when you push to public Strava. If you'd rather attribute to
  your own coach setup (or no one at all), set
  `STRAVA_PUBLISHER_FOOTER_SUFFIX="by My Coach"` in your `.env`. The
  random-gerund prefix stays either way.

The mechanical validator runs a second time inside `push_workouts.py`
as a last-line defence — even if step 5 was skipped or the plan
mutated, no plan with an ERROR finding leaves the script.

### Why this many stages

Each stage exists because a single LLM context that tries to do all of
it loses something:

- A planner that also picks exercises will silently downgrade Pull-day
  stimulus to physio because the wellness slice looks scary
- A specialist that also computes wellness gates will produce a
  plausible-looking workout that violates the rotation rule
- A validator that's part of the planner can't catch its own blind
  spots

So the head coach keeps the stages separated. Slow, but the failure
modes are mostly visible at the right stage.

---

## Requirements

### Software (mandatory)

- **[Claude Code](https://claude.com/claude-code)** — the runtime. The
  plugin runs entirely inside Claude Code; there is no standalone server.
- **Python 3.11+** for the helper scripts (`scripts/`).
- An **[intervals.icu](https://intervals.icu) account** (free). The
  planner reads wellness, the pusher writes workouts, and post-activity
  NOTEs persist athlete feedback there. Without intervals.icu the
  Alex Demo still loads read-only, but no live workflow runs.

  *Why intervals.icu, and not something we built ourselves?* It is free,
  the data model fits a coach (CTL / ATL / TSB, HR zones, planned
  workouts, events and NOTEs are all first-class), and the import layer
  covers basically every tracker that matters — Garmin, Wahoo, Polar,
  Suunto, COROS, Strava, Apple Health, plus manual entry. The
  maintainer has kept the platform open, responsive, and reliable for
  years as effectively a one-person operation. Hats off — this
  framework would not exist without it.

### Hardware (recommended)

- A **GPS watch or cycling computer** that syncs to intervals.icu (any
  of the trackers listed above). Without one, there are no activities
  to plan around.
- A **chest-strap HR monitor capable of R-R recording** (e.g. Polar
  H10) for the optional DFA-α1 zone validation. Wrist-based HR is not
  accurate enough for α1; the protocol explicitly requires a strap.
- A way to measure **body weight** (any scale that syncs to
  intervals.icu / Garmin / Withings). The planner uses body weight for
  pace-power scaling.

### Optional, feature-gated

- **Garmin account + a watch with running-dynamics support (HRM-Pro,
  HRM-Run, or Running Dynamics Pod).** Needed only if you want
  *running-dynamics* — ground-contact time, vertical oscillation,
  stride length, cadence-per-section — overlaid on the video form
  check, and the same fields surfaced in the lap chronicle of
  `/analyse`. Planning, wellness, pushing workouts, post-activity
  feedback, and the form check itself all work without it;
  intervals.icu is enough for those.

  Access goes through the open-source
  [garminconnect](https://github.com/cyberjunky/python-garminconnect)
  library — thanks to **cyberjunky** for maintaining it; without that
  project, this integration would not exist. The library logs in with
  your Garmin email and password (`GARMIN_EMAIL` / `GARMIN_PASSWORD`
  in `.env`) and caches the session token under `cache/garmin-session/`,
  so re-login is rare.

  *Why credentials and not OAuth?* Garmin offers no open developer API
  for third-party apps to pull individual user data. A developer-access
  request for this project was denied. The credential-based downloader
  is therefore the only viable path — used at the athlete's own risk,
  on the athlete's own account. If you are not comfortable with that,
  leave the Garmin block empty in `.env` and the rest of the framework
  keeps working.
- **Video recording device** for the form-check workflow. For
  strength / core / ninja / balance any phone on a tripod is fine. For
  running, the best results come from a **drone with a follow-me mode**
  — the maintainer uses a **DJI Neo 2** (keeps a runner in frame, gimbal
  stable enough for biomechanical analysis). Any drone with a working
  follow-me works; phone-on-tripod gives you only one angle and no
  fresh-vs-fatigued comparison.
- **Strava account (optional)** — only needed for the legacy `strava`
  gear backend and for the title/insights sync (`/strava`, mirrors
  intervals.icu names to Strava). The title/insights sync is **off by
  default** (`STRAVA_PUBLISH_ENABLED=false`) since Strava now returns
  403 on activity writes for apps without `activity:write` scope; enable
  it only once your Strava app holds write access. The default shoe
  backend `intervals` (`SHOE_TRACKING_BACKEND` in `.env.example`) uses
  native intervals.icu gear and needs no Strava access at all.
- **Telegram bot** if you want to talk to the coach from your phone.
- **OpenRouter API key** — required for the video form check
  (`scripts/analyse_video.py` calls Gemini through OpenRouter) and used
  by the planner/specialist prompts whose YAML metadata names an
  OpenRouter model. Swap those prompts for Anthropic models if you
  prefer; the video form check stays on OpenRouter.

### What you do not need

- A subscription to any paid coaching platform.
- A separate database — intervals.icu is the canonical store; the
  framework keeps only ephemeral context in `cache/` and a few JSON
  logs in `data/`.
- A server. Everything runs locally inside your Claude Code session.

---

## Quickstart

See [Requirements](#requirements) above for what you need installed and
which accounts to have ready.

### Option A — Install as a plugin from GitHub

```
/plugin marketplace add airbone42/360-data-athlete
/plugin install aicoach-framework@360-data-athlete
```

The plugin code now lives under
`~/.claude/plugins/marketplaces/360-data-athlete/aicoach-framework/`.
Then, in your project root:

```bash
# 1. Scaffold a wrapper layout from the plugin's template
PLUGIN=~/.claude/plugins/marketplaces/360-data-athlete/aicoach-framework
cp -r "$PLUGIN"/wrapper.example/. ./

# 2. Install the Python deps from the plugin path
pip install -e "$PLUGIN"

# 3. Credentials template (fill in keys you have — Alex Demo runs without)
cp "$PLUGIN"/.env.example .env
```

The canonical 4-step setup walkthrough lives in
[wrapper.example/README.md](wrapper.example/README.md). See
[Plugin layout — what lives where](#plugin-layout--what-lives-where)
below for what should end up in your project root vs. inside the plugin
install directory.

### Option B — Local-path plugin for development

```bash
git clone https://github.com/airbone42/360-data-athlete framework
pip install -e ./framework
cp framework/.env.example .env
```

Add this to your project's `.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "360-data-athlete": {
      "source": { "source": "directory", "path": "./framework" }
    }
  },
  "enabledPlugins": {
    "aicoach-framework@360-data-athlete": true
  }
}
```

Start Claude Code in the project root — it auto-loads the plugin from
the local path (in-place; edits take effect on `/reload-plugins`).

### Plugin layout — what lives where

After install, the plugin code lives at
`~/.claude/plugins/marketplaces/360-data-athlete/aicoach-framework/`
and is **read-only** — treat it as an installed dependency. Your
project root holds the parts that are personal to you:

| Path | Sphere | Owner |
|------|--------|-------|
| `~/.claude/plugins/.../aicoach-framework/` | Framework (public) | Upstream — edit via PR |
| `.claude/settings.json` (your repo) | Personal | You — plugin enablement, hooks |
| `config/` (your repo) | Personal | You — overrides plugin defaults file-by-file |
| `.env` (your repo) | Personal | You — credentials, gitignored |
| `CLAUDE.md` (your repo) | Personal | You — coaching rules layered on top of the framework |
| `data/` (your repo) | Personal | Runtime artefacts (muscle log, audits, approvals) |

The plugin's `app/utils/paths.py` loader looks for `config/` files in
your repo first and falls back to the plugin's `config.example/`
defaults for any file you do not override — so out-of-the-box you can
start with a single edited `athlete_static.md` and grow your override
set over time.

**Quickstart skeleton.** A minimal wrapper layout is bundled with the
plugin at `wrapper.example/`. Copy its contents into a fresh private
repo to start:

```bash
gh repo create my-athlete --private --clone
cp -r ~/.claude/plugins/marketplaces/360-data-athlete/aicoach-framework/wrapper.example/. my-athlete/
```

See [wrapper.example/README.md](wrapper.example/README.md) for the
4-step setup walkthrough.

**Contribution path.** Generic improvements (new validator rule, new
agent, paradigm fix, doc clarification, bug fix with reproduction) go
upstream — open a PR against
[airbone42/360-data-athlete](https://github.com/airbone42/360-data-athlete);
see [CONTRIBUTING.md](CONTRIBUTING.md) for what kind of PR lands.
Athlete-specific tweaks (your zones, your PRs, your injuries, your
equipment, your language) stay in your wrapper repo — never edit the
plugin install directory directly, since `/plugin update` would wipe
your changes.

### First run

The first thing Claude should do is fetch the bundled Alex Demo context:

```bash
python3 framework/scripts/fetch_context.py --date $(date +%Y-%m-%d)
```

For real athlete data, create a `config/` directory next to
`framework/config.example/` and put your own `athlete_static.md`,
`athlete_status.md` etc. there. Files in `config/` override the
framework defaults of the same name.

---

## What you can do today

After install, the plugin exposes these slash commands. They are
namespaced under `aicoach-framework:` — invoke them with the full
qualifier, or wrap them with your own thin project-level commands.

### `/aicoach-framework:training` — Generate today's plan

Plans the day end-to-end: pulls wellness + activities → planner produces
a directive → specialists detail each workout → semantic + mechanical
validation → shoe advisor → push to intervals.icu.

```
> /aicoach-framework:training

[planner] HRV 62 (baseline 60) | TSB +3 | last hard: 4 days ago.
Z2 readiness solid. No ninja yesterday — grip pillar is up.

Plan:
  1. Strength 30min — push/pull complementary, RPE cap 7
  2. Easy run 50min — Z2 (HR 138-148), forest path, GAP-paced

👟 Shoes today: Nimbus 26 (134 km) — Z2 long, road, no plyo today
```

### `/aicoach-framework:analyse i12345678` — Post-session review

Pulls the activity, parses the FIT file, builds sub-laps, then the
data-scientist agent produces a factual lap chronicle and the
coach-analyst writes coaching feedback (max 250 words, GAP-aware on
hilly profiles).

```
> /aicoach-framework:analyse i12345678

## Activity Header
- Distance: 13.43 km, duration: 75:00 min
- Elevation gain/loss: 194 m / 194 m → 14.5 m/km (hilly profile)
- avg pace 5:36/km | GAP 5:28/km (delta +8 s/km — profile averaged out)
- HR zones: Z1 33% / Z2 66% / Z3+ 0%

### Lap 1 (warmup, 0:00–8:00)
HR ramps from 102 to 138 bpm by minute 7 (cardiac startup drift).
Cadence stable around 173 spm. GCT ~245 ms. No surface transition.

[…]

## Coaching feedback
**Session overview** — Solid build run; planned 75 min completed at
106 % compliance. GAP shows consistent Z2 economy, no efficiency
breakthrough yet. […]
```

### `/aicoach-framework:wellness` — Quick status

Pulls context and shows a compact wellness block (HRV, RHR, sleep, CTL /
ATL / TSB, intensity readiness, weather, upcoming events, last 4-week
zone distribution). No plan generated.

### `/aicoach-framework:muscleoverview` — 30-day fatigue map

Per-muscle fatigue based on logged loads, with traffic-light readiness
flags (🟢 trainable / 🟡 moderate / 🔴 rest).

### `/aicoach-framework:audit` — Consistency audit

Scans configs, agents, prompts and external NOTEs for drift, refines
findings via the `config-auditor` subagent (fresh context), and writes
a markdown report. Fixes go through the `config-fixer` (also fresh
context) with an explicit approval log per edit.

The `exercise_progressions.md` slice of the audit
(`check_log_vs_history`) also auto-surfaces at the top of every
`/training` / `/wellness` session via the `configDrift` field of
`fetch_context.py` — so stale exercise entries are visible to the
planner and specialists without having to run `/audit` explicitly. The
explicit `/audit` flow remains the right tool for the full sweep
(HR-zones, orphan muscle IDs, recovery-week consistency,
override-drift, etc.).

Companion script: `sync_description_drift.py` lifts athlete-edited
sets/reps/duration/weight **and hold-time / TUT** values from activity
descriptions back into `config/exercise_progressions.md`, so a 2s→3s
hold progression doesn't sit silently in the activity stream while the
spec still says 2s.

### `/aicoach-framework:strava` — Sync titles + insights to Strava

Mirrors intervals.icu workout names to Strava (all activity types) and
writes the follower-facing insights block on endurance activities via
the `strava-publisher` agent. Idempotent — re-runs skip activities that
already carry the configured footer suffix. Runs automatically as step
6.6 of `/analyse`; manual forms: `/strava`, `/strava --days 7`,
`/strava --activity-id i...`, `/strava --dry-run`.

### `/aicoach-framework:pull` — Fetch git remote

Fast-forward pull on the configured default branch. Generic — works
against GitHub, Gitea, or any git remote.

---

## Training philosophy

The framework defaults follow a small, opinionated set of principles:

- **Polarized distribution.** Target ~80 % low-intensity (Z1/Z2),
  ~20 % high-intensity (Z3/Z4/Z5). Z3 grey zone is actively avoided.
  Sources: Seiler 2010; Stöggl & Sperlich 2014/2015.
- **HRV-gated intensity.** HRV below baseline + 3 days easy → hard Z4/Z5
  blocked. The 🔴 intensity-readiness signal is a soft veto, not a
  suggestion.
- **No advance planning.** Plans are produced same-day from the current
  HRV, sleep, and athlete feeling. No weekly schedule blocks.
- **Deload on evidence, not on calendar.** The `mesoLoadTrend` gate
  inspects CTL trend, week-vs-week ramp, and HRV trend; a recovery week
  is committed for a full 7 days once triggered, not re-decided daily.
- **DFA-α1 zone validation.** When a Z2 run trigger fires (last
  validation > 10 weeks, training pause > 3 weeks, CTL < 30, or athlete
  feedback "feels wrong"), the specialist suggests a Polar-H10-grade
  recording for VT1 detection. Sources: Rogers et al. 2021;
  Doerr et al. 2021.

Full paradigm definitions live in
[config.example/training_paradigms.md](config.example/training_paradigms.md).
Athlete-specific overrides go in your `config/training_paradigms.md`.

---

## Architecture

```
┌───────────────────────────────────────────────────────────────┐
│  Claude Code (terminal or Telegram plugin)                    │
│  ────────────────────────────────────────                     │
│  Plugin: aicoach-framework                                    │
│                                                                │
│       ┌─ planner ─→ specialist-endurance ─┐                   │
│       │                                                        │
│  HEAD─┼─ planner ─→ specialist-complementary ─┤               │
│       │                                                        │
│       └─ planner ─→ specialist-ninja ─────────┤               │
│                                                                │
│       coach-analyst ◀─ data-scientist                          │
│       mental-coach (auto-triggered)                            │
│       video-analyst (on Telegram video)                        │
│       plan-validator (pre-push, fresh context)                 │
│       config-auditor / config-fixer (on /audit)                │
│       physio-consultant / sports-ortho-consultant              │
│                                                                │
└────────┬───────────────┬────────────────┬──────────────────────┘
         │               │                │
   intervals.icu      Strava           Garmin             Telegram
   (workouts +        (gear,           (FIT files,        (chat
    wellness)          activities)      streams)           channel)
```

Each agent runs in its own pane with fresh context. The head coach is
the session driver — it sequences sub-agent calls, integrates their
outputs, and applies cross-workout consistency rules before pushing.

### Sub-agent quick reference

| Agent | Role | Triggered by | Primary inputs | Output |
|-------|------|--------------|----------------|--------|
| `planner` | Strategic daily planner — decides *what* is trained | `/training` start | `fetch_context.py`, `config/athlete_*`, `training_paradigms.md` | plan-directive JSON (workouts[], coaching_notes, active_blocks) |
| `specialist-endurance` | Run / ride structure (pace, zones, intervals.icu format) | per-workout pane after planner (Run / Ride) | planner directive, `fetch_type_history.py`, `exercise_log.md` | workout structure JSON (structure, intervals_icu, focus, surface) |
| `specialist-complementary` | Strength, plyo, core structure (sets, reps, weights) | per-workout pane after planner (WeightTraining / Workout w/o ninja tag) | planner directive, type history, `exercise_progressions.md` | workout JSON with exercises[] |
| `specialist-ninja` | Ninja athletics (5 pillars, grip, push/pull balance) | per-workout pane after planner (ninja tag) | planner directive, type history, pillar rotation | workout JSON with exercises[] |
| `data-scientist` | Factual lap chronicle — no interpretation | `/analyse` after FIT parse | sub-laps JSON, HR zones | per-lap chronicle markdown |
| `coach-analyst` | Coaching feedback on the lap chronicle | `/analyse` after data-scientist | data-scientist output + activity + wellness | feedback markdown (overview / strengths / growth, max 250 words) |
| `mental-coach` | Pre-workout motivation, setback processing | auto-triggered on LONG / RACE / setback / motivation signal; `/mental` | wellness, last 3 activities, free-text context | 3–7 sentence message |
| `video-analyst` | Form check + sports-physiology challenge | Telegram video upload or manual `analyse_video.py` invocation | video frames, athlete restrictions, exercise checklist | execution + drill + challenge block (≤ 10 sentences) |
| `plan-validator` | Semantic plan check before push | `/training` step 3.5b | final plan JSON + mechanical validator output + wellness + last 7 days | findings (ERROR / WARNING / INFO) + clearance |
| `config-auditor` | Drift scanner across configs / agents / prompts | `/audit` | scanner JSON from `audit_consistency.py` | markdown report at `data/audits/...md` |
| `config-fixer` | Implements one audit finding at a time, with approval log | `/audit` after auditor handoff | one finding YAML + audit report path | diff applied + approval log entry + report mark |
| `physio-consultant` | Physiotherapy consultation on injuries / symptoms | athlete invokes manually | symptoms, training history, athlete_static | rehab / load / red-flag assessment (≤ 300 words, with disclaimer) |
| `sports-ortho-consultant` | Orthopaedic consultation, imaging indication | athlete invokes manually | symptoms, training history, athlete_static | differential diagnoses + imaging + return-to-sport (≤ 300 words, with disclaimer) |
| `strava-publisher` | Mirrors intervals.icu titles to Strava + follower-facing insights block on endurance activities | `/strava`, or automatically as `/analyse` step 6.6 | `strava_pending.py` candidates, `fetch_activity.py`, `strava_coupling.py` | title update + 2–4 line insights block + gerund footer |

**Specialization without inheritance.** Plugin agents are generic and
read all athlete-specific facts (PRs, HR zones, injury restrictions,
language) from `config/` at runtime. Athletes don't fork agents — they
override config files. For genuinely athlete-specific workflows that
have no place in the public default, create a project-level agent in
your own `.claude/agents/` (unqualified name); the plugin agent stays
available under its namespaced name (`aicoach-framework:<agent>`).

Full design walk-through:
[docs/architecture.md](docs/architecture.md).

---

## Configuring your own athlete

The framework loads configuration from `config/` (athlete-specific) and
falls back to `config.example/` (framework defaults). To go from demo to
your own setup:

1. Copy `config.example/athlete_static.md` to `config/athlete_static.md`
   and edit (body weight, PRs, injuries, restrictions).
2. Copy `config.example/athlete_status.md` to `config/athlete_status.md`
   and set your current LTHR, HR zones, CTL plan.
3. Copy `config.example/athlete_preferences.md` to `config/` and set
   language, sport priorities, acceptance phrases.
4. (Optional) `competition_plan.md`, `equipment.md`, `exercise_log.md`.

Anything you do **not** override falls back to the demo defaults.

For a fully separated setup (private athlete repo + public framework as
a plugin), see
[docs/architecture.md → "Two-repo layout"](docs/architecture.md).

---

## Glossary

| Term | Meaning |
|------|---------|
| **CTL** | Chronic training load — long-term fitness proxy (~42-day EWMA of training stress) |
| **ATL** | Acute training load — short-term fatigue proxy (~7-day EWMA) |
| **TSB** | Training stress balance = CTL − ATL. Positive = fresh, negative = fatigued |
| **LTHR** | Lactate-threshold heart rate; anchor for HR zones |
| **HRV** | Heart-rate variability (RMSSD), morning resting; readiness marker |
| **RHR** | Resting heart rate |
| **DFA-α1** | Detrended-fluctuation-analysis slope of RR intervals; α1 = 0.75 ≈ VT1, α1 = 0.5 ≈ VT2 |
| **VT1 / VT2** | First / second ventilatory threshold |
| **Z1–Z5** | HR-based intensity zones (Z1 recovery, Z2 endurance, Z3 tempo, Z4 threshold, Z5 VO2max) |
| **GAP** | Grade-adjusted pace — pace corrected for elevation gain/loss |
| **GCT** | Ground-contact time (running dynamic) |
| **RPE** | Rate of perceived exertion (1–10 scale) |

---

## Who is this for

- Structured endurance athletes (running / triathlon) with 5+ years of
  consistent training and a solid sports-physiology vocabulary, who
  want to read along with how the system reasons rather than rely on it
- Operators who are comfortable running Python scripts and editing
  markdown configs
- People exploring how Claude Code behaves as a generic agent harness
  on a non-code domain (with sub-agents, plugins, persistent file
  state, terminal + chat surfaces) — not people looking for a generic
  multi-agent orchestration framework

## What this is NOT

- Not a product, not a service, not training advice
- Not for beginners or anyone without a solid endurance / strength
  training background and medical clearance
- Not hardened against active abuse — see [SECURITY.md](SECURITY.md)
- Not stable — agent definitions, configs, and validator rules evolve
  weekly

### Specifically: the clinical-consultant agents

> ⚠️ **The `physio-consultant` and `sports-ortho-consultant` agents are
> not licensed medical practitioners.** They are conversational
> reasoning tools generated by an LLM, with no examination, no
> palpation, no imaging, no clinical context.
>
> Output from these agents is **not suitable as a basis for
> self-diagnosis or treatment decisions**. In jurisdictions where
> AI-based medical advice is regulated (e.g. EU MDR, Germany / Austria /
> Switzerland), use is at your own legal risk. Always consult a
> qualified human professional for actual care. We provide these agents
> as a debate partner for the head coach — nothing more.

If any of these matter to you, this is not the project for you. Fork it
or move on.

---

## Security

This is an experimental system. Read [SECURITY.md](SECURITY.md) before
exposing it to data you care about. Key points:

- External text from intervals.icu NOTEs, Strava / Garmin activities,
  and athlete messages is **escaped** before injection into LLM prompts
  (`app/utils/sanitize.py`), but this is hygiene, not a hardened
  defence.
- Config-modifying agents (`config-fixer`) log every edit to an
  append-only approval log (`data/approvals/...jsonl`).
- The system trusts the operator's environment — secrets are loaded
  from `.env`, intervals.icu / Telegram / Garmin credentials are yours
  to protect.
- No threat model for compromised athlete accounts, compromised Claude
  setup, or active adversaries.

To report a security issue, open an issue or email
[info@tobiaszander.de](mailto:info@tobiaszander.de).

---

## Who built this and why

[Tobias Zander](mailto:info@tobiaszander.de) — multi-sport athlete
(sub-3 marathon, sub-10h Ironman, both with a human trainer), licensed
fitness trainer and AI enthusiast.

Built for the maintainer's own training. The point of going public is
*not* to recruit users.

The interesting question this project asks isn't "can LLMs coach an
athlete?" — that's obviously a long way off. It's **"how far can Claude
Code go as a generic agent harness when the domain has nothing to do
with code?"** Sub-agents, slash commands, hooks, plugins, MCP servers,
persistent file-backed state — these primitives work just as well for
training planning, where the failure modes are domain-specific
(silent over-conservatism, false-positive pillar attribution, sport-
specific HR-zone confusion) rather than syntactic.

If pure multi-agent orchestration is what you need, LangChain /
LangGraph / AutoGen are the better fit and the LangChain folks have
written more thoughtfully about it than I will. What you might find
useful here is the *harness pattern* — how Claude Code's defaults
(plain-text agents, plain-text configs, plain-file state, terminal +
chat surfaces) compose into something that survives weeks of real-world
pushback from a domain expert who refuses to let the system bluff.

The [architecture doc](docs/architecture.md), `framework/CLAUDE.md`,
and the agent definitions in `agents/` are where the design lives.

---

## License

[MIT](LICENSE). Use it, fork it, build on it — no warranty, no
liability, no obligation to share back.

## Contributing

This project is maintained as a personal experiment. Pull requests are
welcome but not actively solicited — see
[CONTRIBUTING.md](CONTRIBUTING.md) for what kinds of contributions make
sense and what doesn't.
