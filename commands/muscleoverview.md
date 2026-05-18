# /muscleoverview — Muscle fatigue overview

Shows the current fatigue status of all sport-relevant muscles, grouped
by body part.

## Workflow

### Step 1: Run the overview

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/muscle_overview.py
```

Emits a terminal table with:
- **Last load** — when the muscle was last loaded
- **Load** — cumulative load over the last 30 days (S = strength,
  C = cardio)
- **Fatigue** — estimated residual fatigue in % (exponential decay)
- **Next OK** — when the muscle is trainable again (fatigue ≤ 30 %)

Colour code: 🟢 ≤30 % trainable | 🟡 30–65 % moderate | 🔴 >65 % rest

### Step 2: Interpretation

Explain to the athlete:
- Which muscle groups are most fatigued (🔴)
- Which are available for the next session (🟢)
- Notable patterns (e.g. one-sided overload, under-training of certain
  groups)

Keep it short: max 3–5 points, direct and actionable.

### Step 3 (optional): Review unmapped exercises

If the athlete wants to address unmapped exercises:

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/muscle_overview.py --review-unmapped
```

For each unknown exercise: research which muscles are involved and add
to the mapping:

```bash
# Add the mapping manually to config/exercise_muscle_mapping.json
# Then re-run backfill:
python3 "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/log_muscle_load.py --backfill 30 --silent
```

### Step 4 (optional): Backfill

If data is missing (e.g. after a longer pause or a new setup):

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/muscle_overview.py --backfill 30
```

## Notes

- **Phase A:** The system collects data but does NOT enforce hard
  blocks in planning. Data is informational.
- **Scales:** Strength load (S) and cardio load (C) use different units
  and MUST NOT be summed.
- **Recovery times** are based on muscle size and the peak RPE of the
  last session (lookup table in `config/muscle_db.md`).
- **New exercise not in DB?** → add it to
  `config/exercise_muscle_mapping.json`, then run backfill again.
