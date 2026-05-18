# Recovery week protocol (framework defaults)

> Generic deload-week rules used by the planner and audit. Override
> per-athlete values in `config/athlete_status.md` (recovery-week status
> block).

## When to start a recovery week — three gates

The planner suggests a deload (`mesoLoadTrend: "deload recommended"`) only
when **all three** gates pass:

1. **Sufficient base load** — CTL ≥ 24 (athlete is not just rebuilding)
2. **Real fatigue accumulation** — last 7-day TSS ≥ 60 (athlete actually
   loaded the system)
3. **Not a rebuild pattern** — not currently within 14 days of a long
   training break (avoid deloading during the return-to-training ramp)

CTL gate is a default. Athletes with very high base (≥ 60 CTL) can raise it.

## Rules during a recovery week

- **Running:** strictly Z1 / Z2. No tempo, no intervals.
- **Strength / complementary:** volume −20 %. No top sets. Cap RPE at 7.
- **Duration may stay normal** (volume ≠ intensity).
- **Mobility / balance:** unchanged or slightly increased.

## How the status is tracked

Set in `config/athlete_status.md`:

```markdown
## Recovery week status
- active: yes
- start: YYYY-MM-DD
- planned end: YYYY-MM-DD
- reason: <short context>
```

When `planned end` lies in the past, `_compute_planning_constraints`
silently ignores it — the recovery week is effectively over even if the
flag is still `yes`. The Coach should still clean the block manually for
clarity.

## Starting a recovery week (Coach protocol)

1. Verify weekday using Python (`date.strftime('%A')`), not by intuition.
2. Set fields above with start/end dates.
3. Brief the athlete: scope, expected feel, end date.
4. Skip race-pace work, hill repeats, max sets for the duration.

---

## TSB-based override (additional trigger)

Independent of the 3-gate analysis above, **a deload is recommended** when:

- Rolling 7-day mean TSB drops below **-25**, OR
- TSB is below **-30** for 3 or more consecutive days

Rationale: Coggan/Allen TSB-stages indicate "diminishing returns" below -30 — training in this state degrades the fitness it was meant to build. The 3-gate analysis is build-phase-focused; this trigger catches deeply-fatigued accumulation independently. Source: [recovery-week-triggers.md](../research/recovery-week-triggers.md), citing Coggan & Allen 2019 + TrainingPeaks coach consensus.

## Convergence signal (Meeusen-consensus)

When **two or more** of the following signals are red over 3+ consecutive days, the planner should propose deload regardless of 3-gate or TSB triggers:

- HRV below baseline (≥1 × within-athlete CV — see [hrv-rhr-baseline-methodology.md](../research/hrv-rhr-baseline-methodology.md))
- RHR trend +3 bpm or more
- TSB consistently < -15

Rationale: Meeusen et al. 2013 consensus statement — "no single reliable diagnostic marker for OTS exists — diagnosis requires the convergence of multiple indicators over time." Single-marker red is acute, multi-marker red over 3+ days is non-functional-overreaching risk.
