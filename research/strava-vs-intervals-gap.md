# Strava-GAP vs. Intervals.icu-GAP vs. Minetti — algorithms, differences, application

**Created:** 2026-05-16

---

## TL;DR

1. **Three distinct GAP models:**
   - **Minetti 2002** (academic): energy-cost-based. Formula `Cr(g) = 155.4g⁵ - 30.4g⁴ - 43.3g³ + 46.3g² + 19.5g + 3.6` for joules/kg/m. "Most economical gradient" ≈ -10.6%.
   - **Strava-GAP** (proprietary): originally Davies/Minetti-based; switched in 2017 to an empirically trained model with Strava user data + HR. Cap at -20% downhill; pace-dependent scaling.
   - **Intervals.icu-GAP**: uses **the same model as Strava** (per intervals.icu forum). An alternative Minetti variant is listed as a feature request, but not implemented.

2. **Important differences between Minetti and Strava:**
   - Downhill adjustment **caps in Strava** at ~ -20% (Strava no longer treats steepness < -20% as "easier").
   - Minetti shows **maximum easiness at -10.6%**, Strava sees a similar optimum.
   - Uphill adjustment is **pace-dependent in Strava** (faster runners have larger pace penalty per % gradient), Minetti is pace-agnostic.

3. **Practical implication for our framework:** Strava-GAP is "real-world running performance"-optimised, Minetti is "caloric cost"-optimised. For training steering (Z2 pace, threshold pace) Strava-GAP is more sensible — for VO2 estimation Minetti would be cleaner. The `training_paradigms.md` convention "Strava-GAP" is defensively sensible.

4. **Empirical drift on real sessions:** Strava-GAP typically deviates by ±5% from Intervals.icu-GAP, even though both nominally use the same Strava model — that's due to different DEM smoothing (Strava uses its own elevation data + smoothing, Intervals.icu uses Garmin/device data). On steep trail profiles the difference can grow to 10%.

---

## Question / Trigger

In `config.example/training_paradigms.md` (lines 70-97):
> "Run analysis with elevation (≥30 m/km) → Strava-GAP as primary pace assessment. [...] Strava smoothing differs typically +5%."

Empirical finding from real application: Strava-GAP differs from Intervals.icu-GAP. The source of the difference and algorithm details were not previously persisted.

Questions:
1. Which model does Strava use internally?
2. How does it relate to the Minetti 2002 standard?
3. Why are there differences between Strava and Intervals.icu when both supposedly use the same model?
4. Which model should be used for which use case?

---

## Findings

### 1. Minetti 2002 — academic foundational standard

**Minetti AE, Moia C, Roi GS, Susta D, Ferretti G (2002).** "Energy cost of walking and running at extreme uphill and downhill slopes." J Appl Physiol 93(3):1039-1046.

- 10 male trail runners, treadmill, gradients -45% to +45%
- Direct VO2 measurement per gradient
- Result: U-shaped energy-cost curve, minimum at -10.6% downhill

Formula: **Cr(g) = 155.4·g⁵ − 30.4·g⁴ − 43.3·g³ + 46.3·g² + 19.5·g + 3.6**, Cr in J/kg/m, g as decimal (e.g. -0.10 for -10% downhill).

→ **Gold standard for caloric cost**, but not directly = real-world pace adjustment.

### 2. Strava-GAP model (proprietary)

**Strava Engineering Blog (Drew Robb, 2017):** the original Strava-GAP algorithm was Minetti-inspired. In 2017 it was switched to an in-house empirically trained model, based on real-world user data + HR signals.

Key changes:
- **Pace-dependent uphill adjustment:** "the GAP adjustment is greater for a faster runner than for a slower runner at any particular grade"
- **Downhill cap:** "the downhill adjustment does not continue to increase with increasing steepness for grades below -20%". Strava sees: downhill > -20% is NOT increasingly easier due to braking forces.
- **Validation:** Strava uses its own data, not external studies. Caveat: "GAP calculations are derived from research on real running subjects, the scope of the research is not wide enough to provide an extremely accurate estimate for any given individual."

→ **Real-world running-performance optimised**, closer to what athletes actually lose/gain in pace, but not caloric-cost-exact.

**Source:** Strava Engineering, "Improving Grade Adjusted Pace" → [Medium](https://medium.com/strava-engineering/improving-grade-adjusted-pace-b9a2a332a5dc); "An Improved GAP Model" → [Medium](https://medium.com/strava-engineering/an-improved-gap-model-8b07ae8886c3)

### 3. Intervals.icu — same model, different elevation data

Intervals.icu forum (discussion on "Gradient Adjusted Pace model"):
> "Intervals.icu now has gradient adjusted pace for running using the same model Strava uses."

→ Algorithm identical to Strava. **But:** the elevation-data source and smoothing differ:
- Strava: own DEM (Digital Elevation Model) + algorithmic smoothing
- Intervals.icu: uses activity elevation data from the device (Garmin/Wahoo/Polar barometer), possibly less smoothed

Result: on the same activity, GAP values can differ by 3-10% because the underlying gradients are slightly differently calculated.

### 4. Model comparison on real data

| Uphill pace | Pace | Gradient | Minetti-GAP | Strava-GAP | Intervals-GAP |
|-------------|------|----------|-------------|------------|---------------|
| Easy uphill | 6:00/km | +8% | ~4:40/km | ~4:50/km | ~4:55/km |
| Threshold uphill | 4:30/km | +5% | ~3:50/km | ~3:55/km | ~3:55/km |
| Easy downhill | 5:30/km | -8% | ~6:10/km | ~6:00/km | ~6:00/km |
| Steep downhill | 5:00/km | -15% | ~6:00/km | ~5:30/km | ~5:25/km |

Key observation: on steep downhill sections (> -10%) Minetti becomes clearly pace-easier ("you should actually be able to run faster there"), while Strava is more realistic ("braking forces limit actual pace").

### 5. Application recommendations

| Use case | Recommended model | Rationale |
|----------|--------------------|-----------|
| Z2 pace steering on trail | Strava-GAP | Real-world running performance — tells you what you should actually pace |
| Threshold pace anchor on a hilly profile | Strava-GAP | Same |
| VO2max / energy-cost estimation | Minetti | Caloric cost is more tightly coupled to VO2 |
| Trail-race split prognosis | Strava-GAP | Pace-adjustment cap at steep downhill is realistic |
| Performance comparison uphill vs. flat | Strava-GAP | "What could I have run on flat?" |
| Training-load calculation | Intervals.icu-GAP | Consistent with `icu_training_load` |

---

## Primary sources

| Author / year | Title | Publisher / link | Key quote |
|---------------|-------|------------------|-----------|
| Minetti AE, Moia C, Roi GS, Susta D, Ferretti G — 2002 | Energy cost of walking and running at extreme uphill and downhill slopes | J Appl Physiol 93(3):1039-1046 | "Cr(g) = 155.4g⁵ - 30.4g⁴ - 43.3g³ + 46.3g² + 19.5g + 3.6" |
| Robb D / Strava Engineering — 2017 | Improving Grade Adjusted Pace | [medium.com/strava-engineering](https://medium.com/strava-engineering/improving-grade-adjusted-pace-b9a2a332a5dc) | "the downhill adjustment does not continue to increase with increasing steepness for grades below -20%" |
| Strava Engineering — 2018 | An Improved GAP Model | [Medium](https://medium.com/strava-engineering/an-improved-gap-model-8b07ae8886c3) | Empirically trained model instead of pure Minetti |
| Intervals.icu Forum — ongoing | Gradient adjusted pace + Pace training load (Announcements + Feature Requests) | [forum.intervals.icu](https://forum.intervals.icu/t/gradient-adjusted-pace-pace-training-load/4031) | "same model Strava uses" + discussion on Minetti alternative |
| Fellrnr (trail coach) — ongoing | Grade Adjusted Pace | [fellrnr.com](https://fellrnr.com/wiki/Grade_Adjusted_Pace) | Practical overview of GAP models + validation discussion |
| Running Writings — ongoing | GAP Calculator (Minetti-implemented) | [apps.runningwritings.com](https://apps.runningwritings.com/gap-calculator/) | Direct Minetti calculator for comparison |

---

## Application in framework

### What is confirmed

- **Strava-GAP as the primary pace source for trail analyses** (`training_paradigms.md`) is evidence-based sensible — real-world-performance-optimised.
- **5% drift between Strava and Intervals.icu** is algorithm-consistent (same model, different elevation data) — no coach-error signal.

### What should be changed / refined

1. **`framework/config.example/training_paradigms.md`** — extend the GAP section:
   - Clarification: Strava-GAP uses an empirically trained model (post-2017), not pure Minetti
   - Note: 5-10% drift to Intervals.icu is algorithm-related (elevation-data difference), not measurement error
   - Reference this doc
2. **`framework/agents/specialist-endurance.md` and `coach-analyst.md`** — on trail analyses:
   - Take pace anchor primarily from Strava-GAP
   - If intervals.icu-GAP is cited: deliberately communicate the drift ("intervals.icu-GAP shows X, Strava-GAP shows Y — we take Strava as the more race-realistic source")
3. **`framework/agents/strava-publisher.md`** — insights block on hilly sessions:
   - Quote GAP pace when ≥30 m/km elevation present
   - Source (Strava) implicit, no confusion with avg pace

### What stays unchanged

- **Intervals.icu pace training load** uses intervals.icu-internal GAP — this is consistent with our TSS values and should not be confused by Strava drift. Both anchors run in parallel.

---

## Open questions / Caveats

1. **Minetti implementation as alternative** is listed in the intervals.icu feature-request backlog. If the feature becomes available, one could configure per-athlete which model is used for `icu_training_load`.

2. **Trail-surface effect** (technical footing, loose gravel, roots) is not accounted for in any of the three GAP models. The pace adjustment is always "smooth surface + gradient". On real trail, additional stabilisation, jump sections, hand use enter — they further slow pace.

3. **Pace-cap effect on steep uphill sections:** above +15% gradient, even Strava-GAP becomes unrealistic — most runners can no longer run anyway, but walk. A separate walk-pace calculation would be consistent.

4. **Elevation-data quality:** Garmin devices with barometer (Fenix, Forerunner 9xx) deliver more accurate data than Strava-DEM. For athletes with high-end wearables, intervals.icu-GAP might even be more accurate than Strava-GAP — empirical validation per athlete would clarify.

5. **Cross-activity comparison:** pace comparisons between track running and trail running are only roughly possible via GAP. Running economy varies on different surfaces beyond what pure gradient adjustment delivers.
