# /training — Generate today's plan

Build the training plan for today (or a given date).

## Arguments
$ARGUMENTS
Optional: date in `YYYY-MM-DD` format. Default: today.

---

## Workflow

### Step 1: Fetch athlete context

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/fetch_context.py --date {DATE}
python3 "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/log_muscle_load.py --backfill 7 --silent
```

The backfill ensures all activities of the last 7 days are processed in
the muscle profile — even if new sessions came in since the last
`/analyse`. Idempotent, fail-soft; never blocks planning.

Check `dataWarnings`. If present: 1 line to the athlete, then continue.
Check `athleteFeedback`. If not "no feedback": show the feedback to the
athlete (1 line) and make sure to pass it to the planner.
Check `skippedWorkouts`. If present → inform the athlete and clean up:
`python3 "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/delete_workouts.py --event-ids {IDs}`
Check `hrvReviewPending`. If present → **before the planner** ask the
athlete (see CLAUDE.md "HRV-response review"). Persist answer as NOTE,
then continue with step 2.

### Step 2: Launch planner as teammate

Launch the `planner` agent in a pane as a teammate. Hand it:
- The full `fetch_context.py` output (all relevant fields)
- The date
- **`athleteFeedback`** from the context (MANDATORY, even if "no feedback")
- **`activities[-3:]`** — the 3 most recent activities (array is
  oldest-first, NOT `[:3]`!)
- **`weeklyZoneBalance`** — zone distribution over the last 7 days (for
  polarization check)
- **`mesoLoadTrend`** — 4-week load trend (deload recommended or not)

The planner reads `config/` files itself. It presents its proposal in
chat with decision reasoning.

Review the planner output. Give feedback in the planner pane if needed
(e.g. "no ninja today, race in 2 days").

### Step 3: Brief the specialists

For every workout with `duration_min > 0`. **Order: Complementary →
Ninja → Endurance** (strength sets the muscle-group baseline, ninja
reacts to that, endurance is the most independent).

**Start sequentially — not parallel.** Only when specialist N has
presented its `structure` does specialist N+1 start with N's exercise
list as context.

**3a. Load type history** (per workout, before the responsible specialist
starts):
```bash
python3 "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/fetch_type_history.py \
  --date {DATE} --type {type} --tags {tags} --max-sessions {3 for endurance, 5 otherwise}
```

**Tags filter is MANDATORY when the directive carries them.** For a
Quality Run (`tags: ["run", "intervals"]` or contains "intervals"), pass
`--tags run,intervals` — otherwise the unfiltered call returns whatever
the last 3 runs happened to be (often Easy Z2 days), which carries no
progression information for a Quality directive. Same for Quality Ride
(`intervals` tag). The specialist falls back to a second filtered
fetch if the briefed history lacks the matching class, but the head
coach should not depend on that fallback.

*Drift incident pattern:* head coach called `--type Run --max-sessions
3` without `--tags`, briefed 3 Easy Z2 runs; specialist prescribed a
Threshold workout that **regressed** vs. the previous same-class
session (5×5 → 4×5 instead of 5×5 → 5×6 per the KW21 build). Tags
filter on the head-coach side prevents this silently.

**3b. Launch specialist agent in a pane** (routing: Run/Ride →
`specialist-endurance`, ninja tag → `specialist-ninja`, otherwise →
`specialist-complementary`):

In the start prompt, pass:
```
Directive: {workout JSON from the planner}
Type-history: {fetch_type_history.py output — FULL JSON, not summarized!
  The description fields carry "-> Feedback:" / "-> Athlete:" annotations
  — this is the specialist's primary progression memory.}
Wellness: HRV: {hrv} (baseline: {hrvBaseline}) | Sleep: {sleep}/100 | TSB: {tsb}
Last 3 days: {activities[-3:] from context — NEWEST first, WITH descriptions}
HR zones: {context.hrZones}
Weather: {context.weatherInfo}
Other workouts today:
  {for each specialist output already done:}
  - {Workout name} | {duration_min} min | tags: {tags}
    Exercises: {exercise.name} {sets}×{reps/duration} {weight_kg}kg; …
  {not-yet-started workouts: only name + duration_min + intensity, no
  structure}
```

The specialist reads `config/` files itself (incl.
`exercise_progressions.md`) and presents its structure in chat.

**3c. Cross-workout review:**
After all specialist outputs — explicit checklist:
- Same exercise in multiple sessions? → adjust one side or drop
- **Warmup drill duplication (MANDATORY):** running drills (A-skips,
  B-skips, leg swings / hip flexor, ankle bounces, easy calf raises,
  strides) MUST NEVER appear in two consecutive workouts of the same
  day. Rule: **drill belongs in the warmup of the workout with the
  highest matching stimulus** (e.g. A-skips into the run, not into the
  plyo activation before it; hip flexor into the longer session). When
  complementary + endurance fall on the same day → keep the
  complementary warmup minimal, move drills to the run warmup.
- Muscle group from `planningConstraints → yesterday's sessions` heavily
  loaded again today? → load check, replace with accessory or drop
- Wrist/grip: `planningConstraints` shows `⛔ wrist flexor/extensor` when
  relevant — specialists that ignored this get targeted feedback in the
  pane

Add `structure` + `intervals_icu` (if present) to the respective
workout.

**3d. Automatic drill-duplication check (after push):**
`push_workouts.py` automatically runs `check_warmup_overlap.py` after
every push and logs duplications as `WARNING` (fail-soft). When the logs
show a drill duplication — fix directly: delete and re-push with a
cleaned warmup. Manual: `python3 "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/check_warmup_overlap.py --date
YYYY-MM-DD`.

### Step 3.5: Plan validator (MANDATORY, before plan presentation)

**3.5a — Mechanical validator:**
```bash
echo '{workouts_json_array}' | python3 "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/validate_plan.py --date {DATE} --json
```
Output: findings with severity ERROR/WARNING/INFO. Rule IDs (R001 reps
cap, R002 shoulder block, R003 surface field, R004 glute DOMS, R005
achilles+plyo+surface, R006 LTHR drift, R007 pillar duplication, R008
%lthr plausibility).

**ERRORs must be addressed** — either adjust the plan or explicitly
justify ignoring. Presenting the plan to the athlete without addressing
ERRORs is not allowed.

**3.5b — Semantic plan-validator (subagent):**
Launch the `plan-validator` agent as a teammate. Pass:
- Day plan JSON (all workouts with description / intervals_icu)
- Output of `validate_plan.py --json` (mechanical findings as pre-filter)
- Wellness: HRV, TSB, daysSinceIntense
- `activities[-7:]` from context

The subagent checks semantically (pillar rotation, stimulus adequacy,
volume jump, progression consistency with `exercise_progressions.md`,
form findings from `exercise_log.md`).

Review the report. On ERRORs: adjust the plan (in the specialist pane or
yourself). WARNINGs: use judgment.

### Step 4: Present the plan

Show readable markdown with coaching_notes + per workout: name, duration,
focus, structure overview.

**Shoe recommendation (MANDATORY when the plan contains Run or Ride):**
Embed directly in the plan presentation — not after the push:
- Primary shoe: `context.shoeRecommendation.primary.name` + km +
  reason
- Alternative: `context.shoeRecommendation.alternative.name` (if any)
- Warnings: `context.shoeWarnings[]` if present
- Fleet warning: `context.shoeFleetWarning.missing_types[]` if present

Format: `👟 Shoes today: **{primary.name}** ({primary.distance_km} km)
— {primary.reason}`

Ask: "Does that fit, or should I adjust something?"

### Step 5: Feedback loop

**Feedback** → adjust (in the respective pane or yourself), re-present.

**Acceptance** ("ok", "fits", "yes", "good", "go"):
```bash
echo '{workouts_json_array}' | python3 "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/push_workouts.py --date {DATE}
```

`push_workouts.py` invokes the mechanical validator (`validate_plan.py`)
MANDATORILY again before every push — as last-defence, in case step 3.5
was skipped or plan changes happened in between. ERRORs block the push
(exit 2). Override only via `--skip-validation` (emergency, document as
NOTE).

After the main push, `push_workouts.py` **auto-pushes the daily balance
rotation** (rule "Daily balance rotation (mandatory)" from
`framework/CLAUDE.md`) — no extra step needed. The auto-push is
idempotent (skips if a `balance`-tagged event already exists for the
date) and fail-soft (never blocks the main push). Opt out with
`--no-auto-balance` only when explicitly justified (e.g. surgical
recovery day, athlete-requested skip).

"✅ Plan created and pushed to intervals.icu."
