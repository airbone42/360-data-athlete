# HRV and RHR baseline methodology — window, statistics, trigger thresholds

**Created:** 2026-05-16

---

## TL;DR

1. **Our HRV baseline setup: 90-d median, daily value compared directly, 5%-below-baseline triggers `intensityReadiness: 🔴`.** Functionally reasonable, but methodologically standalone between the two mainstream schools (Plews/Buchheit 7d weekly average + SWC vs. Altini 7d moving average + 60d normal band). The 5% threshold is hardcoded in the code, without rationale.

2. **The methodologically recommended approach would be a combination:** 60-d baseline + 7-d rolling average as daily comparison value + Smallest Worthwhile Change (0.5-1.0 × within-athlete CV) instead of a fixed % threshold. That would have two effects: less day-to-day noise (7d smoothing) and athlete-specific sensitivity (CV instead of fixed %).

3. **RHR baseline: currently we compare 3-d average (days 1-3) vs. 3-d average (days 5-7), trigger `delta > 3 bpm` → warning.** That is conservatively calibrated. The literature converges on **+5 bpm against a 3-week baseline as a robust overload marker**; the earlier signal `+3 bpm against a 4-day comparison period` is sensible as an early warning but has a higher false-positive rate (daily sleep-quality drift produces similar values).

4. **Both baselines are stable in single-athlete practice**, but at season changes (massive volume increase, altitude training, longer pause) the 90-d baseline drifts along. That is intended — but prevents "real" adaptation drifts (HRV rises through aerobic adaptation over weeks) from being assessed against a fixed anchor.

---

## Question / Trigger

The framework delivers in `fetch_context.py` two health-check anchors that, in the planner briefing and the pre-planning health-check logic, become direct decision triggers:

- `hrvBaseline` (median over 90 days) and `hrvDeviation` (% deviation today vs. baseline)
- `rhr_trend` and `rhr_trend_delta` (7-d trend in bpm)
- Derived from those: `intensityReadiness` with three levels (🔴/🟡/🟢)

**Where this becomes a drift source:**
- CLAUDE.md "Pre-planning health check": HRV 🔴 → asking the athlete is mandatory
- CLAUDE.md "No silent conservatism": HRV-red status is a trigger for deload decision — if the threshold is miscalibrated, either too many unnecessary deloads occur (5% trigger too sensitive) or too few (too conservative)
- CLAUDE.md "Pre-planning health check" RHR entry: none currently, but the `rhr_trend` output appears in the warnings — an RHR escalation rule could be sensible

Questions:

1. Which baseline window and which statistic (mean/median/rolling average) does the literature recommend?
2. Which trigger threshold for "significantly below baseline" is evidence-based?
3. Which RHR threshold marks early overload?
4. Should both anchors be jointly evaluated (HRV drop AND RHR rise) or independently?

---

## Findings

### 1. HRV baseline schools — two mainstream approaches

**School A: Plews & Buchheit (academic, elite-sport focus)**
- Daily value = **7-d average** (or weekly block) of ln-rMSSD values
- Comparison baseline = medium-long-term (60-90d) or season block
- Trigger = Smallest Worthwhile Change (**0.5-1.0 × within-athlete CV**)
- Rationale: daily rMSSD is too noisy — weekly average only shows training-adaptation trends. "correlations with running performance could only be observed using the average of at least 3-4 days" (Plews & Buchheit 2013).

**School B: Marco Altini / HRV4Training (practitioner, app-scaled)**
- Daily value = **7-d moving average** (rolling, smooths similar to Plews)
- Comparison baseline = **60-d normal band** (visualises the expectation window)
- Trigger = outside the normal band (which practically corresponds to ~SWC)
- Rationale: "we need to shift from a 'higher is better' to a 'normal is better' mentality. … when the daily scores or the baseline are below the band, then it means we have significant stress." (Altini)

**Source:** Marco Altini, "The Ultimate Guide to Heart Rate Variability (HRV): Part 2" → [Medium](https://medium.com/@altini_marco/the-ultimate-guide-to-heart-rate-variability-hrv-part-2-323a38213fbc)

**School C: Kiviniemi / classic (HRV-guided training)**
- Daily rMSSD vs. medium-long-term baseline (4 weeks)
- Trigger = below baseline → easy/off, at/above → planned
- Simple decision rule, clinically validated in endurance studies

### 2. Our framework — positioning

| Aspect | Our implementation | School A (Plews) | School B (Altini) | Assessment |
|--------|--------------------|------------------|-------------------|------------|
| Daily value | Raw single day (today's HRV) | 7-d average | 7-d moving avg | **We are more sensitive to daily noise** |
| Baseline window | 90 days | Season block (60-90d) | 60 days | Conservative-sensible |
| Baseline statistic | Median | Mean (often with outlier filter) | Mean | Median is more robust against outliers ✅ |
| Trigger threshold | -5% baseline (hardcoded) | 0.5-1.0 × CV | Outside normal band | **A hardcoded % is an athlete-agnostic heuristic** |

Implementation in `context_builder.py` lines 304-333 (`_compute_hrv_baseline`):
```python
cutoff = (today - timedelta(days=90)).isoformat()
hrv_values = [d["hrv"] for d in wellness_history if d.get("id", "") >= cutoff …]
baseline = median(hrv_values)
deviation = (hrv - baseline) / baseline * 100
```

Trigger logic in `_compute_intensity_readiness` lines 895-913:
```python
if hrv < float(hrv_baseline) * 0.95:
    return "🔴 No — HRV below baseline"
if tsb < -10:
    return "🔴 No — TSB too negative"
```

### 3. RHR thresholds — literature

**Consensus picture (RunnersConnect, TrainingPeaks, Outside Online, MDPI 2025):**
- **+5 bpm against a 3-week baseline** = robust overload signal (RunnersConnect: "A resting heart rate increase of 5 BPM or more is a strong sign of overtraining")
- **+7 bpm acute** = not-fully-recovered signal (single day)
- **Trend over 2-3 weeks rising** = adaptation risk / overtraining onset
- **Minimum data:** "be sure to record at least three weeks of data" for a valid baseline

**Source:** "How Fatigue, Illness, and Overtraining Impact Your Resting Heart Rate." Runners Connect. → [runnersconnect.net](https://runnersconnect.net/overtraining-resting-heart-rate/)

**Our framework: 3-day average (days 1-3) vs. 3-day average (days 5-7), trigger `delta > 3 bpm`.**

Assessment:
- **More sensitive than the literature standard** (3 bpm vs. 5 bpm) → more early warnings, but higher false-positive rate
- **Very short comparison window (4 days between recent and earlier)** — can be distorted by single stressors (bad night, cycle day, alcohol)
- **Counter-argument:** early warning is explicitly desired — the coach can ignore the hint if the athlete names an obvious explanatory confounder

### 4. RHR and HRV — together or separately?

**Buchheit 2014:** "HRV and HRR respond well to acute changes in training load." Both are autonomic-mediated, both react to sympathetic activation — but RHR is slower and coarser, HRV reacts more acutely.

**Practical recommendation (TrainingPeaks "4 Signs of Overtraining", SimpliFaster):**
- **HRV drop alone:** early stress signal — could be acute stress response (1-2 days)
- **RHR rise alone:** little specific — can be sleep quality, hydration, cycle day
- **Both together over multiple days:** highly specific overload signal — deload trigger

Our framework currently evaluates the two signals **independently** (HRV → `intensityReadiness`, RHR → `warnings` block). A combination rule ("HRV below baseline AND RHR trend +3 → automatic deload proposal in the planner") would be methodologically well grounded.

### 5. Baseline drift on season changes

**Marco Altini:** "we need to shift from a 'higher is better' to a 'normal is better' mentality." The baseline should drift along, because HRV in aerobic adaptation *rises* (enlarged parasympathetic tone) — a fixed baseline would misinterpret adaptation as "above baseline = good".

Our 90-d-median approach is neutral on this: it drifts slowly (~quarterly resolution), which works well for an athlete with a stable training programme, but adapts too slowly with drastic changes (season change, injury break, altitude training). Possible improvement: if `data_points < 30` (e.g. after a 4-week break), weight the baseline or mark it as "uncertain".

---

## Primary sources

| Author / year | Title | Publisher / link | Key quote |
|---------------|-------|------------------|-----------|
| Plews DJ, Buchheit M et al — 2013 | Training adaptation and heart rate variability in elite endurance athletes: opening the door to effective monitoring | [PubMed 23852425](https://pubmed.ncbi.nlm.nih.gov/23852425/) | "correlations with running performance could only be observed using the average of at least 3-4 days" |
| Altini M — n.d. | The Ultimate Guide to Heart Rate Variability (HRV): Part 2 | [Medium](https://medium.com/@altini_marco/the-ultimate-guide-to-heart-rate-variability-hrv-part-2-323a38213fbc) | "we need to shift from a 'higher is better' to a 'normal is better' mentality. … when the daily scores or the baseline are below the band, then it means we have significant stress." |
| MDPI Sensors 2026 | Monitoring Training Adaptation and Recovery Status in Athletes Using HRV via Mobile Devices | [MDPI](https://www.mdpi.com/1424-8220/26/1/3) | "RMSSDMEAN and RMSSDCV should be calculated from a completed 7-day block of daily RMSSD values" |
| Buchheit M — 2014 | Monitoring training status with HR measures: do all roads lead to Rome? | [PMC 3936188](https://pmc.ncbi.nlm.nih.gov/articles/PMC3936188/) | "HRV and HRR respond well to acute changes in training load" |
| Schäfer / RunnersConnect — n.d. | How Fatigue, Illness, and Overtraining Impact Your Resting Heart Rate | [runnersconnect.net](https://runnersconnect.net/overtraining-resting-heart-rate/) | "A resting heart rate increase of 5 BPM or more is a strong sign of overtraining. … record at least three weeks of data" |
| EliteHRV — n.d. | Improving HRV Data Interpretation: Coefficient of Variation | [elitehrv.com](https://elitehrv.com/improving-hrv-data-interpretation-coefficient-variation) | CV = SD/Mean × 100 as additional stress marker |

---

## Application in framework

### What is confirmed

- **Median instead of mean** in `_compute_hrv_baseline` is a sensible robustness choice against outlier days.
- **90-d window** is within the plausibility range (Plews 60-90d, Altini 60d, Kiviniemi 4 weeks) — rather conservative-slow.
- **RHR trend detection with three-day averages** smooths single measurement errors, which is sufficient with Garmin RHR values (which are already smoothed).

### What should be changed / refined

1. **`framework/scripts/` or `app/graphs/sub_athlete_context/context_builder.py`** — new function `_compute_hrv_cv()`:
   - Yields the within-athlete CV of the last 60 days as an additional output
   - Triggers in `_compute_intensity_readiness` via `hrv < baseline - 1.0 × CV` (Plews SWC-1-sigma) instead of fixed `< baseline × 0.95` — athlete-specific
   - Fallback to old logic when CV not computable (< 20 data points)
2. **`framework/CLAUDE.md` — new section "HRV/RHR baseline methodology" or reference to this doc:**
   - Clarification: 90-d median, 5% threshold (mid-term: SWC-based)
   - Clarification: RHR trend checks 3d-vs-3d comparison with 3 bpm trigger; with a trend over 2+ weeks ≥ +5 bpm additional deload trigger
3. **`framework/config.example/recovery_protocol.md`** — add combination rule:
   - "HRV below baseline AND RHR trend +3 bpm AND TSB < -10" over 3+ consecutive days → automatic deload trigger
   - Reference this doc + the recovery-triggers doc (planned H4)
4. **`framework/CLAUDE.md` field table** (lines 40, 157): add hint "see `framework/research/hrv-rhr-baseline-methodology.md` for methodology details".

### What is not changed

- **No migration to ln-rMSSD.** Consistency with intervals.icu display + athlete communication (see HRV forecast doc).
- **No migration to pure 7-d moving average as daily value.** The daily drop is valuable in the athlete workflow ("HRV today 32, yesterday 41 — what was different?") — averaging would hide this diagnostic possibility.

---

## Open questions / Caveats

1. **CV-based trigger not implemented.** The Plews-conformant SWC method (trigger at 0.5-1.0 × CV) is methodologically cleaner than fixed 5% — but computationally more involved and needs an architecture extension. Action item: prototype in a follow-up commit.

2. **Season drift of the baseline not monitored.** If the 90-d baseline HRV systematically wanders (e.g. from 38 to 45 over 3 months of aerobic build), that is from a plan view a *good* development — but is not highlighted in the current output. An additional "baseline-trend" metric (e.g. "baseline +12% over 90d") would be informative.

3. **RHR 3-day comparison window is short.** An additional layer (3-d average vs. 28-d median) would be more robust against single stressor days and closer to the literature standard "3 weeks baseline". Action item: add without replacing the current 7-d comparison (different signal granularities).

4. **Cycle effects in female athletes** are not modelled here (single-athlete repo is male) — for the generic framework application the cycle phase would be an important modulator for HRV baseline (luteal phase typically -10% HRV).

5. **Cross-sport effect on baseline:** for an athlete who within 90 days completely changes the sport mix (e.g. only run → triathlon) the ANS load qualitatively changes. The 90-d baseline then carries mixed data. Rarely a problem in single-athlete context, but a caveat worth noting.
