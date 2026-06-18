# HRV prediction vs readiness classification — is "predict next-day HRV from yesterday's load" the right model form?

**Created:** 2026-06-18

---

## TL;DR

1. **Predicting next-day HRV from a single day's training load via linear regression is not a defensible modeling target at daily resolution.** In the published HRV-guided-training literature, **zero of the methodologically reviewed protocols (0/8 in the Granero-Gallegos 2021 meta-analysis)** use a load→HRV regression forecast — **100% use classification of the current rolling HRV against a baseline band**. Day-to-day HRV is dominated by non-load factors (sleep, life stress, alcohol, measurement noise) such that a single-predictor next-day regression has little signal to recover, and out-of-sample skill against a no-load reference is expected to be at or below zero.

2. **The canonical method is HRV-guided *readiness*, not HRV *prediction*.** The convergent design across Plews/Buchheit, Kiviniemi, Vesterinen, and Altini: track a **7-day rolling mean of ln-rMSSD** and classify each day against a **normal-range band** computed from a **60–90-day reference**, with band width set by either **mean ± 0.5·SD** or the **Smallest Worthwhile Change SWC = 0.5–1.0 × within-athlete CV**. A sustained departure (rolling average below band) is the actionable signal — not a single day's actual-minus-predicted residual.

3. **Load↔HRV coupling is real, but it lives at the chronic-trend timescale (rolling 7d HRV vs rolling load, weeks-scale), not at daily next-day resolution.** Plews 2013 demonstrated that "correlations with running performance could only be observed using the average of at least 3–4 days" — the same applies to load coupling. Even the best multivariable next-day models (Rothschild 2024, LASSO with sleep + RHR + life-stress + 7-day lags) reach only **R² ≈ 0.46 at group level**, and explicitly find that "HRV change predictions depend primarily on changes in HRV over recent days" — not on training load. Load alone has no path to a usable single-day forecast.

4. **Primary recommendation: retire the load→HRV regression as a forecasting tool and replace it with a 7-day rolling ln-rMSSD readiness classifier against a normal-range band.** The existing 90-day median baseline + RHR overload signal (see [hrv-rhr-baseline-methodology.md](hrv-rhr-baseline-methodology.md)) is sufficient as the long-window anchor; the addition is the **7-day rolling daily-value layer** and the **band-width parameter (mean ± 0.5·SD or SWC = 0.5·CV)**. A regression forecast can be revisited later only as a multi-predictor model (≥ sleep, RHR, recent HRV lags), not as a single-load regression — and even then only if a per-athlete walk-forward MAE outperforms a no-load rolling-baseline reference by a documented margin.

---

## Question / Trigger

The framework currently includes a personalised single-predictor next-day load→HRV regression (`hrv_forecast.py` + `_compute_hrv_responses`, documented in [hrv-forecast-model.md](hrv-forecast-model.md)). An out-of-sample walk-forward skill test, run as a one-off audit from real application data, found that the `slope × load` term made the next-day HRV prediction **worse** than a no-load reference at every baseline definition tested (static 90d-median, rolling 7/30/60d medians); slopes were near-zero/positive with 95% CIs spanning 0; a rolling baseline did not recover an acute negative slope. As an immediate band-aid, the framework now emits a `low_signal` verdict when the slope is not statistically significant. This is mechanically correct but leaves the larger question open:

- Is "predict next-day HRV from one day's training load via linear regression" a **defensible modeling target at all** at daily resolution?
- What does the literature actually use — prediction (regression) or classification (band)?
- Does prior-day training load belong in a daily-resolution HRV model at all, or is the load↔HRV signal a chronic-trend phenomenon (weeks-scale rolling-load ↔ rolling-HRV) that a daily regression cannot recover regardless of baseline?
- If the current model form is wrong: **rebuild, retire, or keep-as-is** — with what concrete target design if rebuild?

This is an evidence-gap research flag (`🔬 RESEARCH-FLAG`) on the **model form**, not on athlete-specific calibration.

---

## Findings

### 1. Predictive value of single-predictor next-day load→HRV regression

**The literature does not support next-day load→HRV regression as a usable forecast.** Day-to-day HRV is dominated by non-load drivers; the load fingerprint at 24-hour lag is small relative to the noise floor.

**Magnitude of non-load drivers (next-day HRV deltas):**

- **Sleep quality, single bad night:** "even one night of poor sleep can slash next-day HRV by 15–30%" (WHOOP HRV guide).
- **Alcohol:** "dose-dependent suppression lasting 24–48 hours … one night of drinking potentially decreases HRV for up to five days" (Trail Runner Mag review).
- **Acute psychological stress:** temporarily suppresses HRV; rebounds within hours to days (MindSpire).
- **Measurement artefacts:** posture, time of day, breathing, contact quality — all systematically larger than the next-day load delta typical of a non-peak training day.

**Best-case predictive ceilings, multivariable models with full feature set:** Rothschild et al. 2024 ("Predicting daily recovery during long-term endurance training using machine learning") tracked 43 endurance athletes for 12 weeks (3,572 athlete-days) and built LASSO and linear-mixed models predicting **next-day ln-rMSSD change** from sleep duration, sleep quality, RHR, resting HRV, life-stress, soreness, dietary intake, plus 7-day lags of all of these.

- **Group-level LASSO R² = 0.46 [0.22, 0.51]; RMSE = 0.22** vs. a baseline intercept-only model at RMSE 0.29.
- **Individual-level R² = 0.62 ± 0.14** with the top five variables per athlete.
- **Linear models matched the ML algorithms:** "Both the LASSO and linear mixed models performed well … more complex machine learning algorithms (e.g., XGBoost or Neural Networks) may not be needed in this context."
- **Crucial decomposition finding:** "HRV change predictions depend primarily on changes in HRV over recent days" — not on training load. The dominant predictor of next-day HRV change is the recent HRV trajectory itself; load is a minor contributor in the full-feature model and was not isolated as a stand-alone driver.

**Implication for a single-predictor load→HRV regression:** the model is being asked to recover, from one input, what a 7-day lagged multivariable LASSO captures only as a minority share of explained variance. Even when load coupling is real at a population level (Buchheit 2014: "HRV and HRR respond well to acute changes in training load, with the greater the training load, the smaller the vagal-related HRV"), the daily-resolution next-day signal-to-noise ratio is too low for a 1-predictor regression to beat a rolling baseline. The negative out-of-sample skill found in the empirical audit is the expected outcome, not a calibration issue — there is no signal of usable size to recover with this model form at this temporal resolution.

### 2. The canonical literature method — classification, not prediction

A methodological systematic review and meta-analysis (Granero-Gallegos et al. 2021, PMC8507742) catalogued eight HRV-guided endurance-training protocols. The decomposition of method choice is unambiguous:

| Method family | Studies | Daily value | Reference |
|---------------|---------|-------------|-----------|
| Single-day HRV with moving reference | 4 | Today's ln-rMSSD | 10-day moving baseline |
| Rolling-averaged HRV with fixed reference | 4 | 3- or 7-day rolling mean | 3–4-week fixed baseline |
| **Regression forecast (load → next-day HRV)** | **0** | — | — |

> "All approaches were classification-based readiness assessments comparing current HRV against reference values. The review makes no mention of forecasting next-day HRV from training load as an established method." (Granero-Gallegos 2021)

**Reference-band thresholds across studies:**

- **mean − 1·SD** — 3 studies (stricter, single-trigger drop)
- **mean ± 0.5·SD** — 3 studies (Smallest Worthwhile Change proxy)
- **70% of previous day** — 1 study (legacy Kiviniemi variant)
- **Mean at baseline (no band)** — 1 study

**Convergent operational definition (Plews/Buchheit + Vesterinen + Altini):**

- **Transform:** ln-rMSSD (natural-log-transformed rMSSD) — corrects non-normal distribution, reduces inter-day volatility.
- **Daily value:** **7-day rolling mean** of ln-rMSSD (Plews/Buchheit: "correlations with running performance could only be observed using the average of at least 3–4 days"; Altini HRV4Training Pro: "shows a 7-day moving average (called the baseline)").
- **Reference window:** **60-day normal range** (Altini; Plews 60–90d "season block").
- **Band width:** **mean ± 0.5·SD** (Vesterinen/Javaloyes; HRV4Training shaded "normal range") OR **SWC = 0.5–1.0 × within-athlete CV** (Plews/Buchheit, EliteHRV).
- **Trigger rule:** when the rolling 7-day mean falls **below** the normal range → reduce intensity / rest. When inside the band → planned training. **A sustained departure (multiple consecutive out-of-band days)** is required for a meaningful readiness signal; isolated single-day excursions are noise.
- **CV-as-second-signal (Plews 2012):** in addition to the rolling-mean drop, **rising day-to-day CV** is an independent early indicator of non-functional overreaching — "a lack of day-to-day change in Ln rMSSD may be an indicator of early signs of non-functional over-reaching." Decreasing CV alongside a stable rolling mean = good adaptation; rising CV = autonomic instability even before the mean drops.

**Common decisive feature:** every method uses the **current rolling state** as the decision variable, never the **residual to a load-predicted expectation**. The framing is "where is the athlete now, vs where do they normally sit?" — not "what did yesterday's load predict for today?"

### 3. Does training load belong in the model at all, and at what timescale?

**Acute next-day coupling: weak and inconsistent at daily resolution.** The literature confirms a population-level effect direction (more load → less vagal HRV next morning; Buchheit 2014) but does not demonstrate that this effect, in isolation, is large enough to drive a usable single-predictor next-day forecast for a single athlete. The Rothschild 2024 finding — that the dominant next-day predictor is recent HRV trajectory, not load — generalises this: even when load enters the model, it is a minority contributor.

**Chronic-trend coupling: real, robust, and operates at rolling-7d-to-weekly resolution.** This is where load and HRV genuinely co-move:

- **Plews 2013** — correlations between % change in performance and % change in ln-rMSSD became detectable only when averaging **3–4+ days** of HRV, and reached their useful magnitude at **weekly averages** ("when assessing long-term changes, it is suggested to analyze weekly averages (≥3–4 measurements per week) to increase validity").
- **Plateau finding (Plews 2014b, "How much compliance is needed for valid assessment"):** standardised changes in HRV plateau at **3–4 valid measurements per week** — below this, the signal is dominated by daily noise.
- **TrainingPeaks/Altini convergent practice:** "weekly metrics best reflect chronic adaptation and acute recovery, and averaging HRV over a week provided stronger correlations with fitness improvements than daily measures alone" — rolling 7-day HRV vs rolling-load (CTL) is the timescale at which the load↔HRV relationship becomes operative.
- **Buchheit 2014 framing:** load↔HRV coupling at acute timescale is most visible in **rolling RHR + rolling-HRV trends**, not in single-day load→HRV residuals.

**Conclusion on timescale:** a single-day load → next-day HRV regression is the **wrong temporal instrument** for the relationship it claims to model. The relationship lives at the rolling-7d to weekly trend level. A regression at daily resolution operating on a single load input is structurally mis-matched to the signal it is trying to recover, regardless of baseline definition. This is consistent with the empirical observation that a rolling baseline does not rescue the regression — the issue is not the baseline, it is the modeling target.

### 4. Where load and HRV co-move usefully — the operative integration

Even at the rolling-trend timescale, the literature integrates load and HRV not as a predictor→target regression but as **two parallel monitoring streams**:

1. **HRV stream:** rolling 7-day ln-rMSSD vs 60-day normal-range band → readiness classification (clear / watch / hold).
2. **Load stream:** CTL / ATL / TSB or rolling-7d load → fitness/fatigue/form classification.
3. **Joint interpretation:** rolling HRV trending up alongside steady or rising CTL = productive adaptation. Rolling HRV trending down for 5+ days alongside negative TSB + RHR drift = overload / non-functional overreaching trigger.

This is the integration the framework already implements as the **combined HRV+RHR overload signal** (3+ consecutive days both signals fire → readiness flips red, [hrv-rhr-baseline-methodology.md](hrv-rhr-baseline-methodology.md)). It is the correct integration pattern: parallel state classification with a multi-day consecutive-trigger rule, not a residual-from-prediction approach.

---

## Primary sources

| Author / year | Title | Publisher / link | Key quote |
|---------------|-------|------------------|-----------|
| Granero-Gallegos A, González-Quílez A, Plews D, Carrasco-Poyatos M — 2021 | Heart Rate Variability-Guided Training for Enhancing Cardiac-Vagal Modulation, Aerobic Fitness, and Endurance Performance: A Methodological Systematic Review with Meta-Analysis | [PMC 8507742](https://pmc.ncbi.nlm.nih.gov/articles/PMC8507742/) | "All approaches were classification-based readiness assessments comparing current HRV against reference values. The review makes no mention of forecasting next-day HRV from training load as an established method." (0 of 8 reviewed protocols used a load→HRV regression forecast; 4 used single-day vs moving reference, 4 used rolling-averaged HRV vs fixed reference.) |
| Rothschild JA, Stewart T, Kilding AE, Plews DJ — 2024 | Predicting daily recovery during long-term endurance training using machine learning analysis | [PMC 11519101](https://pmc.ncbi.nlm.nih.gov/articles/PMC11519101/) / [Springer EJAP](https://link.springer.com/article/10.1007/s00421-024-05530-2) | LASSO group-level R² = 0.46 [0.22, 0.51], RMSE 0.22 (vs intercept-only baseline RMSE 0.29) for next-day ln-rMSSD change using sleep, RHR, life-stress, soreness, dietary intake + 7-day lags. "Both the LASSO and linear mixed models performed well … more complex machine learning algorithms (e.g., XGBoost or Neural Networks) may not be needed in this context." "HRV change predictions depend primarily on changes in HRV over recent days." |
| Plews DJ, Laursen PB, Stanley J, Kilding AE, Buchheit M — 2013 | Training adaptation and heart rate variability in elite endurance athletes: opening the door to effective monitoring | [PubMed 23852425](https://pubmed.ncbi.nlm.nih.gov/23852425/) | "Correlations with running performance could only be observed using the average of at least 3-4 days." Rolling 7-day Ln rMSSD + rising day-to-day CV established as the operative monitoring signal. |
| Plews DJ, Laursen PB, Kilding AE, Buchheit M — 2014 | Heart rate variability and training intensity distribution in elite rowers / Monitoring training with HRV: how much compliance is needed for valid assessment? | [PubMed 24334285](https://pubmed.ncbi.nlm.nih.gov/24334285/) | Plateau in standardised HRV changes after 3–4 valid measurements per week — below this, daily noise dominates. Sets the empirical floor for "useful daily value = rolling multi-day average." |
| Buchheit M — 2014 | Monitoring training status with HR measures: do all roads lead to Rome? | [PMC 3936188](https://pmc.ncbi.nlm.nih.gov/articles/PMC3936188/) | "HRV and HRR respond well to acute changes in training load, with the greater the training load, the smaller the vagal-related HRV and the slower the HRR." Direction of effect confirmed at the population level; magnitude at single-day resolution insufficient for a single-predictor next-day forecast. |
| Vesterinen V, Nummela A, Heikura I, Laine T, Hynynen E, Botella J, Häkkinen K — 2016 | Individual endurance training prescription with heart rate variability | (cited in Granero-Gallegos 2021) | Rolling 7-day ln-rMSSD vs normal range = mean ± 0.5·SD; trigger fires when **baseline** (not daily score) falls outside normal band — sustained departure required. |
| Kiviniemi AM, Hautala AJ, Kinnunen H, Tulppo MP — 2007 | Endurance training guided individually by daily heart rate variability measurements | (Original studies, foundational) | Daily rMSSD vs 10-day baseline classification — high-intensity day if HRV ≥ baseline, easy/off if below. First protocolised classification-based design; no regression component. |
| Altini M — n.d. (substack 2024 + HRV4Training Pro docs) | A Brief History of Heart Rate Variability-Guided Training / HRV4Training Pro user guide | [substack](https://marcoaltini.substack.com/p/a-brief-history-of-heart-rate-variability) / [HRV4Training Pro](https://marcoaltini.substack.com/p/hrv4training-pro-overview-page) | Decisions framed as classification — "decisions are binary (adjust intensity or maintain) based on whether HRV falls within, above, or below the normal band." 60-day normal range, 7-day moving baseline, "normal is better" not "higher is better." No regression framing anywhere in the methodology. |
| MDPI Sensors 2026 (Narrative Review) | Monitoring Training Adaptation and Recovery Status in Athletes Using HRV via Mobile Devices | [MDPI](https://www.mdpi.com/1424-8220/26/1/3) | "RMSSDMEAN and RMSSDCV should be calculated from a completed 7-day block of daily RMSSD values" — operationalises Plews protocol for mobile devices; confirms 7-day rolling as state-of-art daily value. |
| Frontiers Physiology 2015 (Buchheit) | Monitoring Fatigue Status with HRV Measures in Elite Athletes: An Avenue Beyond RMSSD? | [Frontiers](https://www.frontiersin.org/journals/physiology/articles/10.3389/fphys.2015.00343/full) | Ln-rMSSD = "most reliable and practically applicable measure for day-to-day monitoring"; recommend "a 7-day running average of LnRMSSD instead of daily measures" to enhance signal-to-noise. |
| WHOOP HRV Guide (practitioner resource) | What is Heart Rate Variability (HRV)? | [WHOOP](https://www.whoop.com/us/en/thelocker/heart-rate-variability-hrv/) | "Even one night of poor sleep can slash next-day HRV by 15–30%" — quantifies the dominant non-load confounder at daily resolution. |
| Trail Runner Mag (practitioner review of literature) | How Alcohol Tanks Your Heart Rate Variability and Sleep | [Trail Runner](https://www.trailrunnermag.com/nutrition/alcohol-recovery/) | Alcohol "creates a dose-dependent suppression lasting 24–48 hours … one night of drinking potentially decreases HRV for up to five days" — second dominant non-load confounder at daily resolution. |

---

## Application in framework

### Recommendation: retire the single-predictor load→HRV regression as a forecasting tool; replace with a 7-day rolling ln-rMSSD readiness classifier against a normal-range band.

The current load→HRV regression forecast is structurally mismatched to the signal it claims to model and does not appear in the published literature in this form. The replacement is the canonical method that every major HRV-monitoring school converges on: classification of a rolling daily value against a normal-range band derived from the athlete's own reference window.

### Target design (replacement readiness classifier)

**Inputs.**

- `ln_rmssd_daily` — natural log of the daily rMSSD value as reported by the wellness source (intervals.icu, HRV4Training, EliteHRV, etc.).
- `ln_rmssd_7d_rollmean` — 7-day rolling mean of `ln_rmssd_daily`. This is the **daily decision variable**, not the raw single-day value.
- `ln_rmssd_60d_mean`, `ln_rmssd_60d_sd` — mean and standard deviation of `ln_rmssd_daily` (or of the 7d rolling mean — both variants exist in the literature; the 60d-of-daily-values variant is more conservative and matches HRV4Training Pro) over the **60-day reference window**.
- `ln_rmssd_60d_cv` — within-athlete coefficient of variation = `60d_sd / 60d_mean`. Used as the SWC anchor.

**Band definition.** Configurable, with two literature-anchored options:

- **Option A (Vesterinen / HRV4Training default):** normal range = `60d_mean ± 0.5 · 60d_sd`.
- **Option B (Plews/Buchheit SWC):** normal range = `60d_mean ± k · 60d_cv` with `k ∈ {0.5, 1.0}` — `k=0.5` is sensitive (more touchpoints), `k=1.0` is conservative.

Both options are operationally equivalent in spirit; the choice is a sensitivity/specificity trade-off, not a methodological disagreement. Recommend **Option A as default** because it does not require a separate CV computation pathway and is the school most explicitly aligned with single-athlete app-scale monitoring; expose `k` as a configurable parameter.

**Verdicts.** Per day, derived from `ln_rmssd_7d_rollmean` vs the band:

| Verdict | Trigger | Planner interpretation |
|---------|---------|------------------------|
| `clear` | 7d rolling mean inside the band | Planned stimulus proceeds; no HRV-driven downgrade. |
| `watch` | 7d rolling mean below the band for **1–2 consecutive days** | Soft signal — proceed but flag in `coaching_notes`. Combine with RHR/RHR-baseline as the joint trigger. |
| `hold` | 7d rolling mean below the band for **3+ consecutive days** | Hard signal — recovery prescription is the default; align with the existing combined HRV+RHR overload trigger (3-day consecutive rule, see [hrv-rhr-baseline-methodology.md](hrv-rhr-baseline-methodology.md)). |
| `above` | 7d rolling mean above the band | Adaptation-positive signal; planner may consider a slight stimulus increase if other systematic signals also clear (taper plan, TSB, restrictions). Not a license to ignore other gates. |
| `insufficient_data` | < 30 valid daily values in the 60-day reference window | Fall back to existing 90d-median + 5%-deviation logic ([hrv-rhr-baseline-methodology.md](hrv-rhr-baseline-methodology.md)). Do not classify until the reference is populated. |

**Why a multi-day consecutive rule for `hold`:** isolated single-day excursions out of the band are noise (a single bad night of sleep can drop the 7d rolling mean below band for one day even with normal training). The Plews/Vesterinen convention requires sustained departure — 3+ consecutive days — as the actionable signal. This aligns with the framework's existing combined HRV+RHR overload signal, which already uses a 3-consecutive-day rule.

**Secondary signal (optional follow-on):** track the day-to-day CV of `ln_rmssd_daily` over the trailing 7 days. A **rising CV** alongside an unchanged rolling mean is an independent early-overreaching indicator (Plews 2012). Implement as an advisory metric `hrvCvTrend` — not a hard trigger initially; promote to trigger only after empirical calibration on the athlete's own history.

### What about training load — does it enter the model?

**Not as a forecasting predictor of HRV.** The two streams remain parallel:

- **HRV stream:** the readiness classifier defined above.
- **Load stream:** CTL/ATL/TSB and `weeklyHardReizeBalance` already in `fetch_context.py`.

The integration point is **joint state classification**, not a regression. The framework already does this correctly via `_compute_combined_overload_signal` (HRV below baseline AND RHR above baseline for 3+ days → `deload`). The replacement readiness classifier slots into this same joint-state pattern, using `7d rolling ln-rMSSD vs band` instead of `single-day raw HRV vs 90d median`.

**A regression forecast could be revisited later** only as a multivariable model (≥ sleep, RHR, recent HRV lags, load) targeting next-day HRV — not as a single-load regression. Even then, the bar for inclusion is a per-athlete **walk-forward out-of-sample MAE that beats the no-load rolling-baseline reference by a documented margin** (i.e. the audit pattern that flagged the current model). This is a follow-on research path, not a default extension.

### Proposed downstream edits (for head-coach approval — NOT applied here)

The following are proposed changes if the recommendation is accepted. All are framework-side (athlete-agnostic); no `config/` changes are required because the new model uses athlete-specific reference statistics computed from the athlete's own wellness history.

| Path | Proposed change |
|------|-----------------|
| `framework/scripts/hrv_forecast.py` | **Retire as a forecasting script.** Either delete or rename to `hrv_readiness.py` and refactor: compute `ln_rmssd_7d_rollmean`, `60d_mean`, `60d_sd`, `60d_cv`; classify against the band; emit `{verdict ∈ {clear, watch, hold, above, insufficient_data}, days_consecutive, rolling_mean, band_low, band_high, cv, cv_trend}`. Remove the slope/intercept/residual-std/significance machinery — none of it is meaningful under the readiness paradigm. |
| `framework/app/graphs/sub_athlete_context/context_builder.py` `_build_hrv_sensitivity`, `_compute_hrv_responses` | Replace with `_compute_hrv_readiness_band` returning the verdict above. The `low_signal` verdict goes away because the model is no longer a regression — there is no slope-significance test to fail. The "did the actual fall outside the personal expectation?" question is replaced by "is the rolling 7d outside the band?" |
| `framework/app/graphs/sub_athlete_context/context_builder.py` `_compute_intensity_readiness`, `_compute_combined_overload_signal` | Wire the new `hold` verdict into the existing combined overload trigger (it already uses a 3-consecutive-day rule, so the wiring is natural). The 5%-below-baseline single-day single-trigger remains as the early-warning layer for the days the 7d rolling mean is still inside band but the daily value drops sharply — same role as the existing `rhrTrend` short-window early warning vs the long-window `rhrBaseline`. |
| `framework/CLAUDE.md` "Planner systematic-input rule" + "No silent conservatism" | Update `hrvForecastLatest.verdict` references: remove `expected`/`needs_review`/`under_stimulus`/`low_signal` vocabulary, replace with `clear`/`watch`/`hold`/`above`/`insufficient_data`. Clarify that the verdict is now a **readiness classification**, not a **forecast residual** — the planner reads it the same way it reads `intensityReadiness`, not the way it reads a model prediction. |
| `framework/research/hrv-forecast-model.md` | Mark as **superseded** with a header pointer to this doc. Keep the file (audit trail of why the regression was retired) — do not delete. Add a one-line TL;DR at the top: "This forecast model is superseded — see hrv-prediction-vs-readiness-modeling.md for the rebuild rationale." |
| `framework/research/README.md` index | Add this doc as `active`. Mark `hrv-forecast-model.md` as `superseded` (new status — extend the index table convention; current statuses are `active`). |
| `framework/research/hrv-rhr-baseline-methodology.md` | Add a cross-reference at the top of "Open questions / Caveats" → "Implemented in `hrv-prediction-vs-readiness-modeling.md` as the readiness classifier: 7d rolling ln-rMSSD vs 60d normal-range band." The "CV-based trigger not implemented" caveat is then resolved by the new doc. |
| `framework/config.example/training_paradigms.md` | If a "HRV forecast — methodology and model assumptions" section exists (from the prior commit), revise it to describe the readiness classifier, not the regression. |

**Note on personal-leak safety:** the readiness classifier is fully athlete-agnostic in design — it uses the athlete's own reference statistics with no hardcoded thresholds, no hardcoded fallback IDs, and no athlete-specific calibration baked into framework code. All thresholds (`k`, `consecutive_days_for_hold`, `reference_window_days`) are configurable defaults in framework code with athlete overrides via `config/athlete_status.md` if needed.

### Alternative considered and rejected: keep-as-is with the `low_signal` band-aid

The current `low_signal` verdict (emitted when the slope's 95% CI includes 0) is mechanically correct — it stops the framework from over-reading noise as a signal. But it is a band-aid that papers over a structural issue: the model has nothing useful to say to the planner most of the time, and the rare days it does say something would, on the literature evidence, be no better than a rolling-baseline classifier would say with higher reliability and better interpretability. Keeping the regression as a primary readiness anchor while the literature uniformly uses a band classifier is a methodology drift the framework should not carry.

### Alternative considered and rejected: retire entirely (no replacement readiness layer)

Retiring the forecast without replacement would leave only the existing 90d-median + 5%-deviation single-day check and the combined HRV+RHR overload trigger ([hrv-rhr-baseline-methodology.md](hrv-rhr-baseline-methodology.md)) as readiness inputs. That is workable but suboptimal: the 90d-median single-day comparison is more sensitive to day-to-day noise than the literature consensus method (7d rolling vs band), and the framework would be missing the smoother daily-decision variable. The rebuild adds the literature-canonical layer at modest implementation cost (the reference statistics needed are simple aggregates over already-available data).

---

## Open questions / Caveats

1. **Band-width parameter calibration.** `mean ± 0.5·SD` (Vesterinen default) vs `mean ± 1·SD` (Kiviniemi original) vs `mean ± k·CV` (Plews SWC) are operationally close but have different sensitivity profiles. Per-athlete optimisation of the parameter would require comparing false-positive vs false-negative readiness flags against subsequent training quality (compliance, decoupling) over a 60–90-day window. Initial default: `0.5·SD` (sensitive — better to catch a real signal late than miss it).

2. **Choice of underlying statistic — daily values vs 7d-rolling values for the 60d reference.** The 60d statistics can be computed from raw daily values (more variance, wider band, more conservative trigger) or from the 7d rolling mean itself (smoother, narrower band, more sensitive trigger). HRV4Training Pro uses the daily-value variant; the rolling-of-rolling variant is more typical of academic papers. Default recommendation: **daily-value variant** for first implementation (matches the practitioner standard); revisit if false-positive rate is high.

3. **Cycle effects for female athletes.** Luteal-phase HRV is typically lower by 5–10% — a 7d rolling mean spanning cycle-phase boundaries can drift the rolling value below band purely for endocrine reasons. The framework currently operates with a male-athlete configuration; for female-athlete deployments, the readiness classifier should be cycle-aware (track cycle phase, evaluate band membership conditional on phase). Plews/Buchheit explicitly flag cycle phase as a confounder. Out of scope for the initial rebuild; documented for the female-athlete generalisation pass.

4. **Confounder annotation pipeline.** The framework already captures `athleteFeedback` (sleep, alcohol, travel, illness) via NOTEs. A future extension could annotate the readiness classifier with confounder context — e.g. "rolling mean below band, but athlete logged 'bad sleep' for 2 of the last 3 days" → soften the `watch`/`hold` decision. Plews/Buchheit and Altini both recommend confounder annotation as the next layer above the band classifier. Implementation: NOTE keyword scan over the trailing 7-day window; out of scope for the initial readiness-classifier rebuild but a natural follow-on.

5. **Per-athlete out-of-sample validation of the rebuild.** The same walk-forward MAE test that surfaced the regression's failure should be run against the readiness classifier — does it produce decisions that line up with subsequent training quality (compliance, decoupling, subjective fatigue)? Action item after the rebuild: 60-day post-deployment audit comparing `hold` days vs subsequent under-performed sessions.

6. **The CV-trend as standalone trigger.** Plews 2012 identified rising day-to-day CV (without a drop in the rolling mean) as an early NFOR signal. Worth implementing as an **advisory** metric in the first rebuild (`hrvCvTrend` field) but **not** as a hard trigger until empirical calibration shows it discriminates over-reach episodes from cycle/sleep noise on the athlete's own history.
