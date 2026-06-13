# Competition plan — Alex Demo

> Demo template. Replace with your own `config/competition_plan.md` listing
> actual target events and ramp phases.

## Season goals
1. Spring 10K — pace personal best
2. Autumn half marathon — sub-1:40

## Target events
| Date | Event | Distance | Surface | Priority |
|------|-------|----------|---------|----------|
| 2026-05-18 | Example Spring 10K | 10 km | road | A |
| 2026-09-21 | Example Autumn HM | 21.1 km | road | A |

## CTL ramp plan (illustrative)
- Now (2026-04): CTL 35
- 4 weeks before 10K: 42
- 10K peak: 45
- 6 weeks before HM: 48
- HM peak: 52

## Tapering rules
- A-races: 10–14 day taper, TSB target +5 to +10
- B-races: 5–7 day taper, TSB target +0 to +5
- After A-races: at least 5 days easy + 1 full rest day, then back to base

## Notes
Keep this file lean. Long-form race reports belong elsewhere (intervals.icu
notes, training log). This file informs the planner about what's next.

## Mesocycle entries — frequency-veto pattern (recommended)

If you add a per-week mesocycle table that prescribes Hard-Reiz **content**
(e.g. "Bergauf-Z4 4–5×5–6 min", "Threshold consolidation", "VO2max block"),
place a one-line frequency-veto reminder next to or beneath the table so
the head coach can't apply a content row in isolation:

> Frequency-veto: Each mesocycle row above defines **content** of the
> week's Hard-Reiz, not its **frequency**. Before applying a row, the head
> coach checks `context.weeklyHardReizeBalance` (rolling 7d, your weekly
> stimulus strategy from `training_paradigms.md`). If the primary-system
> Hard-Reiz of the current rolling 7d is already logged AND no cross-
> training Reiz is still open, the row **defers** to the next week — it
> does not substitute into the primary system. Mechanical safety net:
> `validate_plan.py` R017 (weekly hard-reize cap). Rule rationale:
> `framework/CLAUDE.md` Pre-planning health check §4 (cross-training-slot
> semantics).

This pattern keeps the "content vs. frequency" distinction visible at the
point of use and avoids the drift where an open cross-training slot is
silently turned into a second same-system Hard-Reiz.
