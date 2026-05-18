# config/ — your athlete-specific overrides

Files placed here override the plugin's defaults file-by-file. The
loader chain is:

```
config/  (this directory)
   └─ fallback ──▶  ~/.claude/plugins/.../aicoach-framework/config.example/
```

To customise a file: copy it from the plugin's `config.example/` and
edit it here. Files you do not copy keep using the plugin defaults
automatically.

Typical starting set:

- `athlete_static.md` — age, body weight, PRs, injuries, restrictions
- `athlete_status.md` — current fitness state, LTHR, HR zones, CTL plan
- `athlete_preferences.md` — sport priorities, indoor/outdoor rules,
  coach response language

Optional, copy if you need them:

- `competition_plan.md` — target events, ramp and taper plans
- `equipment.md` — available equipment, weight ranges
- `exercise_progressions.md` — per-exercise load / rep / RPE history
- `exercise_log.md` — form findings, video analysis verdicts
- `training_paradigms.md` — HR zones, polarized/pyramidal, intensity rules
- `recovery_protocol.md` — deload-week rules
- `balance_pool.json` — balance-rotation pool
- `zone_validation_protocol.md` — DFA-α1 step-test protocol
- `muscle_db.md`, `exercise_muscle_mapping.json` — muscle bookkeeping

Path resolution is governed by the plugin's `app/utils/paths.py`
(`CONFIG_DIR`, `CONFIG_FALLBACK`).
