# Current fitness status & reference values — Alex Demo

> Demo defaults. Replace this file with your own `config/athlete_status.md`
> containing real HRV baselines, HR zones, CTL target etc.

## Recovery week status
- **active:** no
- **start:** —
- **planned end:** —
- **reason:** —

## Exercise re-evaluation (trigger config)

Machine-readable input for the exercise re-evaluation trigger
(`context_builder._compute_reeval_trigger` → `planningConstraints` →
`/training`). When a natural boundary is hit the coach re-challenges the
exercise selection against current goals instead of blindly carrying it
forward. Leave the phase plan empty to disable the phase-change trigger;
staleness + recovery-week triggers still work.

- **staleness_weeks:** 6
- **last_reeval_phase:** —

### Phase plan (format: `Phase | start | end`, ISO dates)

A machine-readable mirror of the periodization table in
`competition_plan.md` (the human table stays the documentation source).
Empty by default — fill in per athlete:

```
```

## Reference HR values
- **LTHR (current):** 168 bpm
- **HR max (estimated):** 185 bpm
- **Resting HR:** 50 bpm

## HR zones (5-zone model, ≤ LTHR)
| Zone | Range (bpm) | Purpose |
|------|-------------|---------|
| Z1 (Recovery) | 1–135 | active recovery, easy spinning |
| Z2 (Aerobic base) | 136–148 | aerobic base, long runs |
| Z3 (Tempo) | 149–158 | aerobic threshold, marathon pace |
| Z4 (Threshold) | 159–168 | lactate threshold |
| Z5 (VO2max+) | 169–185 | above threshold, intervals |

## CTL target & ramp rules
- Current CTL: ~35
- Target CTL for next event: 50
- Maximum CTL gain per week: +5 (use `mesoLoadTrend` to throttle)
- TSB sensitivity: stop further load when TSB < −20

## DFA-α1 zone validation (template)
- Last validated: —
- Suspected VT1: — bpm
- Suspected VT2: — bpm
- Stepped-test range (for next validation): start ≥10 bpm below suspected VT1

## Last competition / hard effort
- Date: —
- Event: —
- Result: —
- Notes: —

## Notes on this template
This file is consumed by the planner. Keep field labels stable — the parser
reads them. Add prose freely *after* a field block.
