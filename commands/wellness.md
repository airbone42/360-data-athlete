# /wellness — Quick wellness check

Show current training status without generating a plan.

## Arguments
$ARGUMENTS
Optional: date `YYYY-MM-DD`. Default: today.

---

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/fetch_context.py --date {DATE}
```

Show compactly:

**{dateStr}**
- HRV: {hrvContext}
- RHR: {rhr} bpm | Sleep: {sleep}/100 ({sleepHours})
- CTL: {ctl} | ATL: {atl} | TSB: {tsb}
- Intensity today: {intensityReadiness}
- Weather: {weatherInfo}

**Upcoming events:**
{eventList}

**Zone distribution last 4 weeks:**
{zoneDistribution}

**Cycle hint:** {cycleHint}

If `dataWarnings` is present: show them.

Derive complementary status briefly from `activities` (when was the last
core/plyo/mobility/ninja/legs session).

**Clean up skipped workouts:**
If `skippedWorkouts` is present → inform athlete: "[name] on [date] was
planned but not executed — deleting."
→ `python3 "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/delete_workouts.py --event-ids {comma-separated IDs}`

**HRV-response review:**
If `hrvReviewPending` is present → ask the athlete (see CLAUDE.md
"HRV-response review"). After the answer, persist as NOTE on
intervals.icu.
