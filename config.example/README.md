# config.example/ — framework defaults

This directory ships with the public framework and provides the **fallback
values** the loader uses when a configuration file is not present in the
athlete's private `config/`.

The loader chain is:

```
CONFIG_DIR (athlete-specific, e.g. ./config/)
    └─ fallback ──▶  CONFIG_FALLBACK (here: config.example/)
```

A standalone run with no athlete configuration still works — it operates on
the "Alex Demo" profile defined in this directory.

## How the wrapper overrides

If you set up a private wrapper repo (the framework lives as a submodule
under `framework/`), put your athlete-specific files into `config/` at the
wrapper root. The loader picks your version first, falling back to these
defaults for any file you don't override.

Three patterns of override apply:

1. **Athlete-only files** — only ever exist in the wrapper.
   - `athlete_static.md`, `athlete_status.md`, `athlete_preferences.md`,
     `competition_plan.md`, `equipment.md`, `exercise_log.md`
   - Demo versions here are placeholder/Alex Demo for standalone runs.

2. **Generic-only files** — usually exist only here in `config.example/`.
   - `balance_pool.json`, `exercise_muscle_mapping.json`,
     `training_rules_endurance.md`, `training_rules_strength.md`,
     `training_rules_planner.md`, `muscle_db.md`, `exercise_checklist.md`,
     `zone_validation_protocol.md`, `recovery_protocol.md`
   - Wrapper typically does **not** copy these — relies on framework defaults.
   - Anything athlete-specific (active injury blocks, equipment models)
     lives in the athlete files above and gets referenced from these rules.

3. **Override files** — exist in both, wrapper version is the source of truth.
   - `training_paradigms.md` — framework version uses zone-labels and
     generic weekly examples; wrapper version uses athlete's concrete BPM
     and athlete-specific weekly structure.
   - `exercise_progressions.md` — framework version contains exercise
     definitions + progression vectors only; wrapper version adds
     `Aktueller Stand:` tracking lines per exercise.

## File status

| File | Status | Notes |
|------|--------|-------|
| `athlete_static.md` | EN — Alex Demo | 35y / 70 kg recreational athlete |
| `athlete_status.md` | EN — generic | LTHR/zones template |
| `athlete_preferences.md` | EN — generic | defaults + acceptance phrases |
| `equipment.md` | EN — generic | demo shoe profiles in YAML, no Strava IDs |
| `competition_plan.md` | EN — empty template | one example race |
| `exercise_log.md` | EN — empty | filled by `scripts/analyse_video.py` |
| `recovery_protocol.md` | EN — generic | deload-week defaults |
| `training_paradigms.md` | DE — generic | zone-labels not BPM; wrapper may override |
| `exercise_progressions.md` | DE — generic | exercise defs without tracking; wrapper adds tracking |
| `training_rules_endurance.md` | DE — generic | TODO: translate |
| `training_rules_strength.md` | DE — generic | TODO: translate |
| `training_rules_planner.md` | DE — generic | TODO: translate |
| `muscle_db.md` | DE — generic | TODO: translate |
| `exercise_checklist.md` | DE — generic | TODO: translate |
| `zone_validation_protocol.md` | DE — generic | TODO: translate |
| `balance_pool.json` | DE strings — generic | TODO: translate exercise names |
| `exercise_muscle_mapping.json` | mostly language-neutral keys | exercise aliases include some German |

Files marked **TODO: translate** are functional in their current form but
keep German section headings and prose; English translations welcome.
