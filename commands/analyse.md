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
- **ERG-trainer power is not an athlete signal (MANDATORY).** On an
  ERG-controlled smart trainer the device holds target watts whatever the
  athlete is doing, so a flat power trace is the trainer working, not the
  rider. Never report "power held to the last rep", "zero decay", "watts
  never dropped" as a strength, a finding, or evidence of adaptation, and
  never gate a progression on it. What stays valid from such a session is
  **repetition count** (volume compliance), **cadence**, **HR** and
  **RPE** — cadence being the variable that actually carries muscular
  capacity, since it falls when the athlete runs out while power does
  not. Check `config/equipment.md` for the trainer and its control mode
  before analysing any indoor ride; where the mode is unknown, assume ERG
  for a structured session and state the assumption. Prescribed watt
  anchors remain valid as *dose* — only the inference from held watts
  back to athlete state is invalid.
- **GCT on recovery runs:** High GCT during slow jogging is biomechanics,
  not error. Only evaluate GCT as a fatigue indicator when the GCT rise
  disproportionately exceeds the pace slowdown (pace-normalized). Do not
  comment negatively on absolute GCT values in recovery phases.
- **Cool-down running dynamics are out of scope (MANDATORY).** The
  cool-down is run at a shuffle — far below any pace the athlete trains
  at — and gait at that speed is a different movement pattern, not a
  slower version of the same one. Ground-contact time, vertical
  oscillation, step length, cadence and contact balance measured there
  describe the shuffle, not the session. Restrict every running-dynamics
  statement, trend and fresh-vs-fatigued comparison to the warm-up-
  completed main block; never close a dynamics argument with a cool-down
  value, and never let a claim about persistence ("the shift had not
  recovered by the end") rest on cool-down data. State the excluded
  window rather than silently trimming it. The same applies to the
  post-interval jog segments inside a session.

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
Errors are swallowed — this step does not block the analysis.

### Step 6.6: Activity-name reality check

Before presenting, verify the activity **name** matches the actual
setting. When a planned outdoor session was executed indoor (or vice
versa — `trainer` flag, `type: VirtualRun`/`VirtualRide`, athlete
feedback), surface terms in the inherited plan name become wrong
("Forstweg" on a treadmill session). Fix the name in intervals.icu via
`IntervalsClient.update_activity_name` (replace the surface term:
"Forstweg"/"Trail"/"Asphalt" → "Laufband"/"Indoor", or insert the real
surface on the outdoor case). Skip silently when the name already fits.

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
