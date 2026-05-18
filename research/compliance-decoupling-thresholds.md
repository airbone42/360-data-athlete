# Compliance and decoupling thresholds — reprogram trigger after quality session

**Created:** 2026-05-16

## TL;DR

1. **Decoupling 5% = aerobically fit, 10% = needs more base** is the established Friel/TrainingPeaks threshold. Above 10% = over-paced or fatigued, ≤5% = solid aerobic base.
2. **Compliance 95% as reprogram threshold** is a practice convention (coach standard), not study-verified. But: at compliance < 95% on structured reps a 1:1 repeat is interpreted as "stimulus pressure missed" and the next prescription should be adapted.
3. **Pw:HR decoupling (bike)** and **NGP:HR decoupling (run)** are isomorphic concepts. EF (Efficiency Factor) shows absolute aerobic efficiency, decoupling shows drift within a session.
4. **When to react:** decoupling > 10% AND compliance < 95% in the same session → hard reprogram trigger (reduce volume or intensity). With only one of the two markers → single data point, a second incident within 14 days triggers reprogram.

## Findings

**Decoupling (Pw:HR or NGP:HR):**
- Calculation: EF comparison (power or NGP divided by HR) between first and second session half. Decoupling = (EF₁ - EF₂) / EF₁ × 100.
- **< 5%:** aerobic base solid, the athlete carries the load over the session duration without significant cardiac drift.
- **5-10%:** borderline — on long sessions normal drift, on threshold reps a warning sign.
- **> 10%:** over-pacing or insufficient aerobic base. "Above 10% means more zone 2 before you add intensity" (Friel/TrainingPeaks consensus).

Joe Friel introduced the concept in "The Cyclist's Training Bible"; TrainingPeaks has operationalised it in the help center for years as a standard metric.

**Compliance:**
- Practical definition: reps actually completed or watt-average hits / target × 100.
- Convention: ≥ 95% = "fits", 80-95% = "hold" (repeat, do not progress), < 80% = "step down".
- No direct study source for the 95% threshold — it is a coach convention broadly applied in practice (Allen Lim, Friel, newer performance coaches).

**Combination of both markers:** in a 30/15 incident from real application (compliance 87% + decoupling 19%) both markers were red — that is the unambiguous reprogram trigger. The `vo2max-short-intervals.md` logic (compliance < 95% OR decoupling > 10% → volume and/or intensity reduction before 1:1 repeat) is consistent with the established Friel methodology.

## Primary sources

| Author / year | Title | Publisher / link | Key quote |
|---------------|-------|------------------|-----------|
| Friel J — (ongoing) | The Cyclist's Training Bible (5th ed) + Workout Analysis | [joefrieltraining.com](https://joefrieltraining.com/workout-analysis/) | "AeT mainset decoupling should be no greater than 5% if you are aerobically fit" |
| TrainingPeaks Help Center | Aerobic Decoupling (Pw:HR and Pa:HR) and Efficiency Factor (EF) | [help.trainingpeaks.com](https://help.trainingpeaks.com/hc/en-us/articles/204071724-Aerobic-Decoupling-Pw-Hr-and-Pa-HR-and-Efficiency-Factor-EF) | Operationalisation of the decoupling calculation |
| TrainingPeaks Blog | Are You Fit? All About Aerobic Endurance and Decoupling | [trainingpeaks.com](https://www.trainingpeaks.com/blog/aerobic-endurance-and-decoupling/) | "if an athlete's decoupling is consistently 5% or less for steady-state aerobic workouts then his or her aerobic endurance is sound" |
| Roadman Cycling — 2026 | Aerobic Decoupling for Cyclists — Cardiac Drift, Pa:HR, EF Guide | [roadmancycling.com](https://roadmancycling.com/blog/aerobic-decoupling-cycling-cardiac-drift) | Practice overview with 5%/10% threshold table |

## Application in framework

- **`framework/agents/specialist-endurance.md`** lines 99-122 (compliance ≥95% + decoupling ≤10% as reprogram threshold) is consistent with Friel/TrainingPeaks standards.
- **Reference to this doc + cross-reference to [vo2max-short-intervals.md](vo2max-short-intervals.md)** (compliance check before quality repeat).
- **Code-extension idea (phase 4):** `fetch_activity.py` could inject decoupling and EF as derived metrics into the `activities[]` data, so specialists can consistently check not only compliance but also decoupling.

## Open questions / Caveats

1. **Compliance threshold 95% not study-based** — a deliberate coach convention. For less experienced athletes 90% might be more sensible, for elite closer to 98%. Athlete-specific calibration possible.
2. **Decoupling on short sessions (< 30 min)** is not meaningful (too little data for stable EF comparisons). Threshold reps with 4×3 min Z4 + rests cannot be cleanly "decoupled".
3. **HR lag** (HR rises 1-2 min after power increase) creates artificial decoupling in the first 10 min. Decoupling calculations should exclude the initial warm-up (Friel standard: measure from minute 10).
