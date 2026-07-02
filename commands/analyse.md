# /analyse — Activity analysis

Analyse a completed training session.

## Arguments
$ARGUMENTS
Required: intervals.icu activity ID, e.g. `i12345678`

---

## Workflow

**Analysis standard (MANDATORY):**
- FIT file + sub-laps is the primary data path — intervals.icu streams
  alone are not enough
- **Compliance — one canonical definition:** direct compliance = actual
  vs. planned, computed by the analysing agent itself from activity +
  plan data. The **precomputed `compliance` property** from intervals.icu
  is unreliable — it is never cited and never used as a gate; coaching
  feedback never comments on it
- **GCT on recovery runs:** High GCT during slow jogging is biomechanics,
  not error. Only evaluate GCT as a fatigue indicator when the GCT rise
  disproportionately exceeds the pace slowdown (pace-normalized). Do not
  comment negatively on absolute GCT values in recovery phases.

### Step 1: Load athlete knowledge + activity (parallel)

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/fetch_activity.py --activity-id {ID}
```

Read in parallel: `config/athlete_static.md`, `config/athlete_status.md`,
`config/equipment.md`.

### Step 2: Fetch athlete context

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/fetch_context.py --date {activity_date}
```

### Step 3: Load and parse FIT file (parallel)

**Guard:** If `activity.source == "MANUAL"` or `activity.stream_types ==
null` (manually logged session without Garmin recording) → skip steps 3
and 4. Data-scientist is dropped. Coach-analyst works directly from the
description (step 6).

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/download_fit.py --date {activity_date}
python3 "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/parse_fit.py --fit-path {fit_path}
```

### Step 4: Build sub-laps

```bash
echo '{"streams": {...}, "fit_records": [...], "laps": [...]}' | \
  python3 "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/build_sub_laps.py
```

### Step 5: Lap chronicle (data-scientist)

Launch the `data-scientist` agent in a pane. Pass:
- Sub-lap data from step 4
- HR zones from `context.hrZones`

The data scientist produces a factual chronicle per lap (HR-zone
transitions, running dynamics, surface). No interpretation.

### Step 6: Coaching analysis (coach-analyst)

Launch the `coach-analyst` agent in a pane. Pass:
- Lap chronicle from the data scientist
- Activity data (planned workout, actual values)
- HR zones from `context.hrZones`
- Athlete context (wellness_brief, recent_training)

Structure: **Session overview** | **Strengths** | **Growth areas**.
Max 250 words.

### Step 6.5: Log muscle load (silent)

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/log_muscle_load.py --activity-id {ID} --silent
```

Errors swallowed silently — this step does not block the analysis.

### Step 6.55: Assign shoe gear (intervals.icu backend only)

Only when `SHOE_TRACKING_BACKEND=intervals` (the default) **and** the
activity is a `Run` / `VirtualRun`:

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/set_activity_gear.py --activity-id {ID} --auto
```

Sets the shoe-advisor's recommended shoe on the finished activity so
intervals.icu accumulates the mileage natively. Idempotent — skips if
the activity already carries a gear_id (the athlete may have assigned it
themselves; they can always correct the choice in intervals.icu).
Errors are swallowed — this step does not block the analysis. With the
legacy `strava` backend this step is skipped (the recommendation was
written as a footer at push time instead).

### Step 6.6: Sync Strava (title + insights)

**Skip this step entirely when `STRAVA_PUBLISH_ENABLED` is `false`**
(the default — see `app/config.py`). Strava returns 403 on activity
writes for apps without `activity:write` scope, so the feature ships
off; `strava_pending.py` then reports no candidates and any
`strava_apply.py` write is a no-op. Only run this step once the gate is
set to `true` with a write-scoped Strava app.

Launch the `strava-publisher` agent in a pane and pass:

```
Argumente: --activity-id {ID}
```

The agent mirrors the intervals.icu workout name to Strava (always) and
— for endurance activities — writes a follower-facing insights block
plus a random-gerund footer (`{Gerund} {STRAVA_PUBLISHER_FOOTER_SUFFIX}`;
suffix default `by 360° Data Athlete`, configurable; whole block can be
disabled via `STRAVA_PUBLISHER_FOOTER_ENABLED=false`). Idempotent via
the configured footer suffix: re-running on an already-enriched
activity skips the description silently. Errors do not block the
analysis flow.

**Verify the push actually landed (MANDATORY — do not trust the agent's
report).** A subagent can compose a title/insights block and report
success without the write ever reaching Strava (e.g. the push was
refused by the raw-HR / elevation-drift / duplicate-anchor guard in
`strava_apply.py`, and the failure was not surfaced). After the agent
returns, the head coach re-checks mechanically:

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/strava_pending.py --activity-id {iv_id}
```

The push landed only if, for this activity, the Strava `current_name`
matches the title the agent intended to push (NOT the Strava default
like "Nachtlauf" / "Afternoon Run") **and** (for endurance with
`insights_eligible == true`) `has_insights_anchor == true`. The primary
proof is `strava_apply.py`'s own `strava_status == "OK"` +
`strava_returned_name`; `strava_pending.py` is the independent
cross-check.

> **Caveat — do NOT gate on `name_needs_update == false`.** That flag
> compares Strava against the *canonical intervals.icu name mirror*, so
> it stays `true` whenever an **intentional non-mirror title** is in
> play — e.g. a wrapper rule that writes a translated / localised /
> gag title that deliberately differs from the intervals name. Using
> `name_needs_update == false` as the success signal would report a
> correctly-synced override as "failed" on every run. Verify the
> *content landed* (`current_name` is the intended title and not the
> Strava default; `has_insights_anchor == true`), not that it matches
> the mirror.

If the content is still un-synced (Strava still shows its default name,
or `has_insights_anchor == false`), the agent's push silently failed —
the head coach applies it directly (deterministic fallback), using
**zone language only, no raw HR**, and an elevation number only if it
matches Strava's value (else omit):

```bash
printf '%s' "{zone-language insights block + footer}" | \
python3 "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/strava_apply.py \
  --activity-id {sv_id} --title "{title}" --description-stdin
```

Confirm `strava_status == "OK"` in the result, then re-run
`strava_pending.py` to verify `name_needs_update == false`. Only then is
the Strava step complete.

**Drift incident pattern** (canonical case): the publisher composed a
Dutch title + insights with a raw-HR citation ("124 HF"); the raw-HR
guard refused the push, the activity stayed at its Strava-default name,
and the agent still reported the sync as done. The athlete noticed
nothing had arrived. Fix: this mechanical post-publish verification gate
+ the agent-side Step 6.5 confirmation in `strava-publisher.md`.

### Step 6.7: Sync description drift

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/sync_description_drift.py --activity-id {ID}
```

Compares the activity description (athlete may have edited it on the
event before training or on the activity after training) against the
`**Aktueller Stand:**` lines in `config/exercise_progressions.md`. When
load, sets, reps, or hold-duration of a known exercise has changed and
falls outside the documented range, the line is rewritten in place with
a `(DD.MM.YYYY, iNNNNNN, Athlet-Edit)` stamp. Form notes, progression
vector, and pflicht-setup blocks remain untouched. Endurance sessions
are skipped silently.

Output is visible (not silent) so the athlete sees what was changed and
can correct it. Errors are swallowed — sync failure does not block the
analysis.

### Step 7: Present + feedback

Show the analysis. Ask: "How was the session for you?"

**Feedback** → react briefly (1 sentence), adjust the analysis in the
coach-analyst pane (max 3×).

**Acceptance** ("ok", "thanks", "fits", "good") or empty reply:
```bash
python3 "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/post_message.py \
  --activity-id {ID} --message "Coaching feedback:
{final_analysis}"
```

"✅ Analysis saved."
