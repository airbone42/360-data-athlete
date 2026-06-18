# HRV forecast model — load→HRV regression in the framework

**Created:** 2026-05-16

> **Status: SUPERSEDED.** The load→HRV regression forecast described here has
> been retired. An out-of-sample walk-forward test found the load term had no
> predictive value for next-morning HRV. It is replaced by a 7-day-rolling
> ln-rMSSD readiness classifier against a 60-day normal band — see
> [hrv-prediction-vs-readiness-modeling.md](hrv-prediction-vs-readiness-modeling.md)
> for the rebuild rationale and design. This document is kept as the audit
> trail of why the regression was retired.

---

## TL;DR

1. **Our model is a personalised linear regression** with only one predictor: `expected_delta_pct = intercept + slope × daily_load` (load = `icu_training_load`). Baseline = 90-day median of HRV. Verdict zones: ±1 res_std = "expected", outside ±1.5 res_std = "flagged".
2. **State-of-the-art is methodologically more complex**, but our approach stands in a long, established line (Kiviniemi algorithm, Plews & Buchheit). The main three methodological best practices of the literature — (a) ln-rMSSD instead of raw HRV, (b) 7-d rolling average as the daily value, (c) Smallest Worthwhile Change (SWC) = 0.5-1.0 × CV as trigger — are **not all** implemented in our model. Points (b) and (c) are the biggest gaps.
3. **Verdict zones ±1.5 res_std are narrower than the literature recommendation.** Plews/Buchheit set the SWC at 0.5-1.0 × within-athlete CV — at a typical rMSSD CV of 15-20% that corresponds to ±7.5-20%, i.e. a broader tolerance band. Our ±1.5 σ over a regression residual distribution can come out significantly narrower, leading to **more false-positive "flagged" verdicts**.
4. **A model validation against the internal forecast-vs-actual comparison history** (output of `hrv_forecast.py --json`) is the next concrete step — *before* the model is further extended.

---

## Question / Trigger

In the framework HRV forecast verdicts are treated as a systematic planner input:

- CLAUDE.md "Planner systematic-input rule": before the planner briefing `hrvForecastLatest.verdict` must be checked
- CLAUDE.md "No silent conservatism": if `hrvForecastLatest.verdict == "expected"`, the coach MUST NOT silently throttle down to recovery mode just because HRV is below baseline

That makes the forecast model a key input. But:

- **Which method** sits in the background? (linear regression vs. non-linear vs. ML)
- **Which training-load input** is used? (TRIMP? TSS? Custom?)
- **Which baseline calculation?** (90-d median in our case)
- **Which trigger thresholds?** (±1.5 σ in our case)
- **How validated** is the prediction quality individually?

Questions to sport science:

1. Which methods for HRV prediction are validated and standard?
2. Which load inputs show the strongest correlation with next-day HRV?
3. Which baseline and trigger thresholds does the literature recommend?
4. Where does our model stand in comparison (what do we get right, what should be improved)?

---

## Findings

### 1. Method landscape — from decision rules to deep learning

**Classic pioneer: Kiviniemi algorithm** (Kiviniemi et al. 2007, 2010): compares the daily rMSSD value with a rolling baseline. If below the trigger threshold → easy or off day; if at/above baseline → planned training. **Simple decision rule**, no forecast component. But: considered gold standard of HRV-guided-training studies.

**Plews & Buchheit (2014, "Monitoring training status with HR measures: do all roads lead to Rome?")** establishes the methodological discipline for field application:
- **ln-rMSSD** (natural log transformed) instead of raw rMSSD, because rMSSD is not normally distributed and the log transform reduces inter-day volatility
- **Weekly average over daily values** for correlative statements about adaptation — "correlations with running performance could only be observed using the average of at least 3-4 days"
- **Smallest Worthwhile Change (SWC):** 0.5 or 1.0 × within-athlete coefficient of variation (CV) as trigger threshold
- **Standing recording** recommended for endurance athletes (higher parasympathetic sensitivity)
- **5-10 min upon awakening** as standard protocol

> Plews/Buchheit (2014): "short-term (5-10 min) measurements of HR(V) upon awakening in the morning". "correlations with running performance could only be observed using the average of at least 3-4 days". "changes in a given measure should be interpreted by taking into account the error of measurement and the smallest important change".

**Current front: machine learning** (Frontiers Sports & Active Living 2025, MDPI 2026): ensemble models (Random Forest, Gradient Boosting) and LSTMs combine HRV with sleep, RHR, respiration, prior load → better next-day prediction than single-marker approaches. **But:** an ML black box is suboptimal for our drift-protection goals — we want the coach to be able to understand the model.

### 2. Which load input?

**TRIMP (Training Impulse):** Banister's method from the 1980s, calculated as duration × HR-based intensity weighting. Used as load anchor in practically all HRV studies.

**TSS (Training Stress Score):** Coggan/Allen — power-based (bike) or pace-based (run). Conceptually isomorphic to TRIMP, but more objective with watt data.

**`icu_training_load` (intervals.icu):** hybrid — uses HR-based TRIMP with HR data, pace/power-based anchors when available. Functionally equivalent to TSS/TRIMP for our purposes. Consistent across sports (run, bike, strength), which would require mixed calculations with TRIMP/TSS.

**Key finding:** "HRV and HRR respond well to acute changes in training load, with the greater the training load, the smaller the vagal-related HRV and the slower the HRR" (Buchheit 2014). → Slope sign should be negative (more load → less HRV next day). Our model doesn't check this explicitly — if the personalised regression yields a positive slope, that's a warning sign for either too-little data or too-many confounders (illness, alcohol, sleep disruption).

### 3. Baseline calculation

| Method | Who recommends | Rationale |
|--------|----------------|-----------|
| 7-d rolling average | TrainingPeaks (best-practice meta), Roadman Cycling | Detect trends fast, but sensitive to outliers |
| 30-d rolling average | EliteHRV (standard app) | More robust, slower trend detection |
| 60-90 d baseline + 7-d rolling for daily value | Plews & Buchheit, MDPI 2026 narrative review | Separates chronic adaptation (60-90d) from acute status (7d) |

**Our framework: 90-d median.** Median rather than mean is robust against outliers (illness spikes, cycle days, single measurement errors). 90 days as baseline window is on the conservative side (more data, slower adaptation to seasonal drifts) — but for our purpose (computing the forecast expectation, not detecting trends) sensible.

**Gap:** we have no separate 7-d rolling average for the *daily comparison*. We compare the **single value** of the next day directly against the expected delta vs. baseline. That makes us more sensitive to single-day measurement noise (sleep position, breathing, stress) than the Plews protocol.

### 4. Trigger thresholds — SWC vs. ±1.5 σ

**Plews/Buchheit SWC method:**
- Calculate the within-athlete CV of rMSSD values across the baseline period
- Smallest Worthwhile Change = 0.5 × CV (sensitive) to 1.0 × CV (conservative)
- Daily values outside the SWC band → meaningful change

For an athlete with rMSSD CV of 15% (typical for well-trained endurance athletes), SWC would be ±7.5% to ±15% baseline deviation.

**Our model ±1.5 res_std:**
- Residual σ of the personal regression is NOT the HRV CV, but the scatter around the load→HRV expectation line
- If load already explains most of the HRV variation, res_std is *smaller* than the raw CV → trigger threshold is narrower
- At res_std = 5%, ±1.5 σ would be ±7.5% deviation from **expectation** (not baseline)

**Implication:** our model is potentially **stricter** than the Plews recommendation. A "flagged" verdict can also occur at smaller absolute HRV drops if the personal regression has found a stable prediction corridor. That is not inherently bad, but can lead to **more false positives** — and in the framework context "flagged" → planner should trigger the HRV-review-pending mechanism, which is an athlete touchpoint.

### 5. Validation approach for our output

Our script outputs a `recent_compare` block with `--json` (forecast vs. actual for the last 10 days). With it, calibration can be empirically checked:

- **If model well calibrated:** ~68% of `actual_pct` lie within the CI68 (±1 res_std), ~95% within ±2 res_std. "Expected" verdicts should cover ~70% of days.
- **If model under-fitting:** slope ≈ 0 or wrong sign → load has no predictive value for the respective athlete in this period. **This is now gated explicitly:** `_build_hrv_sensitivity` returns the slope's standard error and `_slope_is_significant` tests whether its 95% CI excludes 0. When the slope is not significant, the per-day verdict is `low_signal` (see below) — the model declares its own lack of signal instead of dressing noise up as "expected".
- **If model over-fitting:** res_std very small, many "flagged" verdicts → unrealistically narrow expectations
- **If data_points too small:** the SE of the slope is large → the slope is insignificant → `low_signal` (the too-little-data case is subsumed by the significance gate; the old "uncertain"-verdict TODO is now implemented this way).

> **Empirical note (generic):** out-of-sample testing on real athlete data can show the single-predictor next-day load→HRV slope to be statistically indistinguishable from 0 even with *adequate* data-point counts — a rolling baseline does not necessarily recover a signal (a confounding fitness trend is not the same as a masked acute signal). Decide per athlete with an out-of-sample skill test (walk-forward MAE in ms against a no-load reference), not with in-sample slope magnitude.

---

## Primary sources

| Author / year | Title | Publisher / link | Key quote |
|---------------|-------|------------------|-----------|
| Buchheit M — 2014 | Monitoring training status with HR measures: do all roads lead to Rome? | [PMC 3936188](https://pmc.ncbi.nlm.nih.gov/articles/PMC3936188/) | "HRV and HRR respond well to acute changes in training load, with the greater the training load, the smaller the vagal-related HRV and the slower the HRR. A regular monitoring of these variables can substantially improve the training process." |
| Plews DJ, Buchheit M et al — 2013 | Training adaptation and heart rate variability in elite endurance athletes: opening the door to effective monitoring | [PubMed 23852425](https://pubmed.ncbi.nlm.nih.gov/23852425/) | "correlations with running performance could only be observed using the average of at least 3-4 days" |
| Kiviniemi AM et al — 2007/2010 | Endurance training guided individually by daily heart rate variability measurements | (Original studies, foundation for HRV-guided) | Daily rMSSD vs. baseline-decision-rule established as standard |
| MDPI Sensors 2026 (Narrative Review) | Monitoring Training Adaptation and Recovery Status in Athletes Using HRV via Mobile Devices | [MDPI](https://www.mdpi.com/1424-8220/26/1/3) | "RMSSDMEAN and RMSSDCV should be calculated from a completed 7-day block of daily RMSSD values" |
| Frontiers Sports 2025 | Mapping HRV in sports science: from monitoring to machine learning | [Frontiers DOI](https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2025.1714962/full) | Method landscape from decision rules through regression to ML |
| EliteHRV (practitioner resource) | Improving HRV Data Interpretation: Coefficient of Variation | [elitehrv.com](https://elitehrv.com/improving-hrv-data-interpretation-coefficient-variation) | SWC = 0.5-1.0 × within-athlete CV as practicable daily threshold |

---

## Application in framework

### What is confirmed

- **A linear model approach is legitimate** as a bridge between the Kiviniemi decision rule (too simple) and ML black box (too opaque). As long as the slope signs are plausible (negative: more load → less HRV), the method is viable.
- **`icu_training_load` as load input** is equivalent to TRIMP/TSS for our purposes — no change needed.
- **90-d median as baseline** is conservative-sensible. Median > mean for outlier robustness.
- **Minimum data-point requirement (≥10 pairs)** is sensible, could be raised to ≥20 (Plews studies work with significantly more data).

### What should be changed / refined

1. **`framework/scripts/hrv_forecast.py`** + **`context_builder` (`_build_hrv_sensitivity`, `_compute_hrv_responses`)** — implemented:
   - **Slope significance, not just sign:** `_build_hrv_sensitivity` returns the slope's standard error (regression dof n-2); `_slope_is_significant` tests whether the 95% CI excludes 0. The `slope > 0` sanity warning now fires only on a *significantly* positive slope — a near-zero slope routinely sits within ±1.96·SE of 0 and used to trigger a false alarm.
   - **`low_signal` verdict:** when the slope is not significant, both the production verdict (`_compute_hrv_responses`) and the script emit `verdict: "low_signal"` instead of expected/needs_review/under_stimulus. The load term has no detectable predictive value, so the planner must not lean on it.
   - **Still open:** the ±1.5 σ verdict threshold is hardcoded; comparing it with the Plews SWC method and making it configurable remains a TODO.
2. **`framework/CLAUDE.md` — "Planner systematic-input rule"** — reference to this doc and clarification:
   - `hrvForecastLatest.verdict == "expected"` means: personal model sees the drop as load-induced, not as an unexplained signal
   - `verdict == "low_signal"` means: the load→HRV slope is statistically indistinguishable from 0 — the forecast is uninformative. The planner treats it as **neither** a green light nor a red flag: no manufactured conservatism, fall back to the other systematic signals (CTL, TSB, taper, restrictions, athleteFeedback).
   - `verdict == "needs_review"`/`"under_stimulus"` means: drop/rise bigger than the (significant) personal model would expect — HRV-review-pending is triggered (`/wellness` workflow)
3. **`framework/config.example/training_paradigms.md`** — new section "HRV forecast — methodology and model assumptions":
   - Reference to this research doc
   - Clarification: forecast is a personal regression, not a generic value
   - Note for coaches: unusual model behaviour (slope sign, large res_std) → empirically validate before blindly following the verdict

### What is not changed

- **Switching to ln-rMSSD is not done.** intervals.icu delivers HRV in milliseconds without log transform. A log transform would break consistency with other framework tools (wellness display, Telegram reports) and presumably bring only marginal accuracy gain because the personal regression on % delta to baseline already uses a scale-invariant endpoint.
- **Switching to 7-d rolling for the daily value is not done for now.** intervals.icu delivers daily values, and the athlete evaluates HRV daily based on the intervals.icu display. Averaging would hide day-to-day variation that is important in athlete communication ("yesterday was 32, today 41 — what was different?"). The trade-off is deliberate.

---

## Open questions / Caveats

1. **Empirical model validation is pending.** The `recent_compare` history should be quantitatively evaluated for the respective athlete: do actually ~68% of the actuals lie in the CI68? If not, the model is mis-calibrated. Action item: after 30 more days of data, write an audit `data/audits/<date>-hrv-forecast-calibration.md`.

2. **A linear model approach is possibly too simple.** Real-world HRV response is non-linear (threshold effects, carry-over from the previous day, acute stressors). An extension to "expected_delta = f(today_load, yesterday_load, sleep_score)" with non-linear terms is conceivable, but data-hungry. Only after 6+ months of data does the model extension pay off.

3. **Verdict thresholds not athlete-specifically calibrated.** ±1.5 res_std is a global constant in the code. An athlete-specific calibration (based on the daily HRV CV of the athlete) would be Plews-conformant and avoid false positives for particularly stable athletes and false negatives for volatile ones.

4. **Confounder handling is not modelled.** Illness, travel, alcohol, sleep disruption are all strong drivers of HRV — but are not taken as inputs into the model. This information lives in NOTEs and in the `athleteFeedback` field; an integration would be conceivable (NOTE keywords "sick", "alcohol", "slept badly" → exclude those days from training data or include them as confounder features).

5. **Cycle effects (for female athletes):** the framework is operated here as a single-athlete setup; in a multi-athlete application the cycle phase would be a relevant modulator for female athletes. Plews/Buchheit mention cycle effects explicitly as a confounder.
