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

## RHR overload threshold (machine-readable)

- **rhr_overload_bpm:** 5

The bpm rise above the RHR baseline that counts as one of the three markers
in `_compute_combined_overload_signal` (HRV below baseline / RHR elevated /
TSB below its threshold). A day counts when **two of the three** are available
and firing; three consecutive such days produce a `deload` verdict.

**This default is a convention, not a literature value.** It was documented as
literature-anchored until a source audit found the attributed sentence absent
from the cited article. The number was kept because changing a readiness gate is
a training decision, but it is athlete configuration — like `impact_streak_max`
— because the right value depends on the athlete's own RHR variability.

What makes the signal specific is the convergence requirement (two markers
agreeing) plus the consecutive-day rule, not the size of the bpm step. Lower
the value for a more sensitive gate, raise it if the verdict fires on days that
feel unremarkable.

## Balance cadence (machine-readable)

- **balance_sessions_per_week:** 7

How many balance / proprioception units the auto-push places per rolling
7-day window. **The default of 7 is the framework's historical behaviour** —
one unit on every training day — and an athlete who leaves this alone sees no
change.

Lower it when the balance work is a real prevention block rather than a short
daily drill. Programmes that measurably reduced lateral ankle sprains ran
**2–3 sessions per week** of progressive, perturbation-based work; there the
useful shape is a longer, harder session at a lower frequency, and a daily
push crowds the week without adding the stimulus that carries the effect.

Two behaviours follow automatically from a value below 7:

- A **minimum gap** of `7 // sessions_per_week` days, so three a week means
  every other day rather than three in a row.
- **Rotation stepping.** The pool holds four sessions and the date-based pick
  (`ordinal % 4`) assumes daily execution — at a two-day gap it keeps drawing
  the same keys. Below 7 the push steps on from the previous session's key
  instead, so all four stay in rotation.

Counting uses planned events, not completed ones: the scheduler's job is not
to double-book the calendar. Execution gaps are a separate question and are
already covered by the `balance` due-warnings in the planning context.
