# Recovery-week triggers — 3-gate logic against sport-science standards

**Created:** 2026-05-16

---

## TL;DR

1. **Our 3-gate setup is solidly calibrated** for "build-phase detection". Gate 1 (CTL threshold) prevents deloads in the rebuild, Gate 2 (last-week minimum load) prevents deloads without real stimulus, Gate 3 (rebuild-after-pause pattern) prevents false positives after pauses. Plus the main check: 4 weeks progressive load → deload recommended.
2. **The canonical sport-science recommendation is a 3:1 microcycle** (3 weeks build, 1 week recovery) — that is exactly the granularity our 4-week rolling-window analysis implicitly checks. With `is_progressive == True` across 4 weeks the 3:1 rule is violated, which is why a deload is signalled.
3. **What is missing in the framework:** convergence signals from *other* sources (HRV trend, RHR rise, subjective fatigue) are NOT aggregated as a deload trigger. The Meeusen consensus recommendation is explicit: "no single reliable diagnostic marker for OTS exists — diagnosis requires the convergence of multiple indicators over time."
4. **TSB as a secondary trigger is missing explicitly.** The literature is unambiguous: **TSB < -30 for consecutive days = deload trigger** independent of CTL progression. Our framework has `TSB < -10 → 🔴 intensityReadiness`, but no aggregate over multiple days TSB < -20 or -30 as a recovery-week trigger.

---

## Question / Trigger

Recovery-week triggers are referenced in CLAUDE.md as systematic input multiple times:

- "Planner systematic-input rule": race-taper window + deload CTL threshold + HRV forecast as 3 inputs
- "No silent conservatism": coach must NOT silently activate deload mode without a hard trigger
- Recovery weeks are **decided once + held in full** (`recovery_protocol.md`)

Implementation in `_compute_meso_load_trend()` (lines 767-844):

1. **Gate 1 — CTL threshold:** if `ctl < deload_ctl_threshold` (default 24, athlete-override possible) → no deload, rebuild
2. **Gate 2 — last-week minimum load:** if last-week TSS < 60 → no deload
3. **Gate 3 — rebuild-after-pause pattern:** if first 2 weeks' average < last week × 35% AND first 2 weeks < 60 TSS → no deload (build after pause)
4. **Main check:** all 4 weeks progressive (no week > 10% below predecessor) → ⚠️ deload recommended

Questions:

1. Are the gate thresholds calibrated? (CTL ≥ 24, TSS ≥ 60, 10% tolerance, 35% rebuild ratio)
2. Should TSB be a standalone trigger, independent of load progression?
3. Should HRV/RHR convergence signals be integrated?
4. Which microcycle structures are evidence-based (3:1, 4:1, 2:1)?

---

## Findings

### 1. Fitness-fatigue model as foundation

**Banister 1975** established the fitness-fatigue model (FFM): performance = fitness – fatigue, each training stimulus raises both components with different decay constants.

In modern operationalisation (Coggan, TrainingPeaks):
- **CTL** (Chronic Training Load) = exponential 42-d smoothed mean of daily TSS → represents fitness
- **ATL** (Acute Training Load) = exponential 7-d smoothed mean → represents fatigue
- **TSB** (Training Stress Balance) = CTL - ATL → "form", positive values = rested, negative = fatigue-accumulated

**Source:** Eric W. Banister, "Modeling Elite Athletic Performance", in Physiological Testing of the High-Performance Athlete (1991). Operationalisation via TrainingPeaks: TrainingPeaks Coach Blog, "A Coach's Guide to ATL, CTL & TSB" → [trainingpeaks.com](https://www.trainingpeaks.com/coach-blog/a-coachs-guide-to-atl-ctl-tsb/)

### 2. TSB-based deload triggers

The literature converges on a TSB staging:

| TSB value | Meaning | Recovery recommendation |
|-----------|---------|--------------------------|
| ≥ +5 to +15 | Race form / peaking | Race day |
| -10 to +5 | Productive build | Continue building |
| -20 to -10 | "Tipping point", standard build | Normal build, monitor |
| -25 to -20 | "Approaching fatigue limit" | Observe, monitor RPE — at rising RPE: deload |
| < -30 | "Diminishing returns" | **Deload recommendation — training in this range degrades the fitness it is meant to build** |

> "If an athlete's CTL is climbing steadily but TSB remains deeply negative, it's time for a recovery block." (TrainerRoad / Roadman Cycling, consensus statement across multiple practice sources)

**Practical deload recommendation from the literature:** 30-40% volume reduction for 1 week, hold intensity but reduce rep count, TSB may climb back to -10. **CTL falls slightly** — that is intended and productive recovery.

Our framework currently has this TSB signal only as a single-day check (`TSB < -10` → `🔴 intensityReadiness`), but **no multi-day-aggregated TSB signal** as a deload trigger. That is a gap.

### 3. Microcycle standards — 3:1 is the default

**Issurin block periodisation** establishes 2-4-week mesocycles with concentrated workloads in "accumulation → transmutation → realization" order. In endurance application the **3:1 microcycle structure** dominates (3 progressive weeks + 1 recovery).

> "In a typical four-week block, the first three weeks progressively overload your body, while the fourth week focuses on recovery. This represents a 3:1 ratio of training to recovery." (TrainerRoad / TrainingPeaks consensus)

**Source:** Issurin VB (2008). "Block periodization versus traditional training theory: a review." Journal of Sports Medicine and Physical Fitness. Plus systematic review: [PMC 6802561](https://pmc.ncbi.nlm.nih.gov/articles/PMC6802561/)

**Transfer to our 3-gate logic:**
- We check 4 rolling 7-day windows for progressive build → that is exactly the 3:1 structure (3 build weeks + observation window). If `is_progressive == True`, the 3:1 recovery obligation is "overdue" — deload signalled.
- Our model is **structurally consistent with Issurin/3:1**. What we do not implement: alternative structures like 2:1 (acute phases) or 4:1 (endurance builds with high-endurance athletes). These must be athlete-specifically overridden via `deload_ctl_threshold`.

### 4. Functional vs. non-functional overreaching — Meeusen consensus

**Meeusen et al. 2013 (Joint Consensus Statement ECSS / ACSM):** define 3 categories of chronic fatigue:

| Category | Performance drop | Recovery time | Markers |
|----------|------------------|---------------|---------|
| Functional overreaching (FOR) | Days to 1 week, then supercompensation | 1-2 weeks recovery | Subjective fatigue, slight HR drift |
| Non-functional overreaching (NFOR) | 2+ weeks performance deficit | Weeks to months | Multiple markers converge — HRV, RHR, mood, sleep, performance |
| Overtraining syndrome (OTS) | > 2 months | Months to > 1 year | Psychological, neuro-endocrine, immune |

**Core statement of the consensus:** "no single reliable diagnostic marker for OTS exists — diagnosis requires the convergence of multiple indicators over time." A single metric is NOT enough — only the joint occurrence of multiple signals (HRV drop + RHR rise + subjective fatigue + performance drop + possibly sleep disruption) is diagnostically robust.

**Source:** Meeusen R et al (2013). "Prevention, diagnosis, and treatment of the overtraining syndrome: joint consensus statement of the European College of Sport Science and the American College of Sports Medicine." Plus practice transfer: NSCA, "Functional and Nonfunctional Overreaching and Overtraining" → [nsca.com](https://www.nsca.com/education/articles/kinetic-select/functional-and-nonfunctional-overreaching-and-overtraining/)

**Transfer to our logic:** currently we evaluate HRV, RHR, TSB as **independent** signals (HRV → `intensityReadiness`, RHR → `warnings`, TSB → `intensityReadiness`). A **convergence rule** (at least 2 of 3 signals "red" over 3+ days → automatic deload proposal in the planner) would be Meeusen-conformant and would make our framework stricter.

### 5. CTL threshold — sport-specific or universal?

**Roadman Cycling, Vitruve, Coggan & Allen:** recommend calibrating the CTL anchor for deload decisions athlete-specifically — typically CTL 30-50 for ambitious amateurs, 60-100 for elite. **Our default of 24** is low — deliberately, because the framework must also support rebuild phases.

`deload_ctl_threshold` as an athlete override in `athlete_status.md` is exactly the right construct — the default 24 is a framework-safe default for "the athlete has not yet accumulated enough to justify a recovery week".

---

## Primary sources

| Author / year | Title | Publisher / link | Key quote |
|---------------|-------|------------------|-----------|
| Banister EW — 1991 | Modeling Elite Athletic Performance | Physiological Testing of the High-Performance Athlete, Human Kinetics | Fitness-fatigue model as foundation for CTL/ATL/TSB |
| Coggan AR, Allen H — 2019 | Training and Racing with a Power Meter (3rd ed) | Velo Press, book | TSB stages, CTL operationalisation, deload recommendations |
| Issurin VB — 2008 | Block periodization versus traditional training theory: a review | J Sports Med Phys Fitness; systematic review: [PMC 6802561](https://pmc.ncbi.nlm.nih.gov/articles/PMC6802561/) | "2-4 weeks mesocycles with highly concentrated workloads … accumulation → transmutation → realization" |
| Meeusen R et al — 2013 | Prevention, diagnosis, and treatment of the overtraining syndrome: joint consensus statement of ECSS and ACSM | Med Sci Sports Exerc | "no single reliable diagnostic marker for OTS exists — diagnosis requires the convergence of multiple indicators over time" |
| TrainingPeaks Coach Blog — 2019 | A Coach's Guide to ATL, CTL & TSB | [trainingpeaks.com](https://www.trainingpeaks.com/coach-blog/a-coachs-guide-to-atl-ctl-tsb/) | TSB ≤ -25 = approaching fatigue limit; ≤ -30 = diminishing returns |
| TrainerRoad Blog — 2021 | Training Periodization: Macro, Meso, & Microcycles | [trainerroad.com](https://www.trainerroad.com/blog/training-periodization-macro-meso-microcycles-of-training/) | 3:1 microcycle as standard endurance structure |
| NSCA — Kinetic Select | Functional and Nonfunctional Overreaching and Overtraining | [nsca.com](https://www.nsca.com/education/articles/kinetic-select/functional-and-nonfunctional-overreaching-and-overtraining/) | FOR vs NFOR vs OTS definitions + recovery times |

---

## Application in framework

### What is confirmed

- **3-gate architecture** is methodologically consistent with Issurin 3:1 block periodisation. The gates prevent false positives in rebuild and low-load phases.
- **CTL threshold with athlete override** is the right architecture — default 24, individually raisable for high-CTL athletes.
- **10% deload tolerance** in the progressivity check is sensible (small week-to-week fluctuations should not justify recovery).
- **Recovery-week duration of 1 week + 30-40% volume drop** in `recovery_protocol.md` matches the TrainingPeaks/Coggan practice recommendation.

### What should be changed / refined

1. **`framework/app/graphs/sub_athlete_context/context_builder.py` — `_compute_meso_load_trend()`** extend:
   - **Additional TSB-based trigger:** if TSB of the last 7 days on average < -25 OR < -30 on 3+ consecutive days → deload signal independent of the progressivity check
   - **Convergence signal** (optional, phase 2): if HRV drop > baseline CV AND RHR trend +3 bpm AND TSB < -15 over 3+ days → "NFOR risk" warning with deload recommendation
2. **`framework/config.example/recovery_protocol.md`** — extend "When to start a recovery week":
   - 3-gate logic remains primary trigger
   - Additionally: "TSB < -25 over rolling 7d OR < -30 for 3+ consecutive days → deload, regardless of load-progression analysis"
   - Reference this doc and [hrv-rhr-baseline-methodology.md](hrv-rhr-baseline-methodology.md)
3. **`framework/CLAUDE.md` — "Planner systematic-input rule"** — extend the field table (lines 445-453):
   - New row: `tsb_trend` (rolling 7-d TSB mean) as an additional deload signal input
   - Source reference to this doc

### What is not changed

- **Default `deload_ctl_threshold = 24`** stays as the framework default; individual adjustments continue via `athlete_status.md`.
- **Recovery-week duration of 1 week** stays fixed — the literature is consistent that 7-10 days suffice for CTL preservation + ATL reduction in productive recovery (Coggan).

---

## Open questions / Caveats

1. **TSB trigger not yet implemented.** The extension in `_compute_meso_load_trend()` is a concrete code change in the next commit cycle (separate patch). Should first be validated against historical data (would the trigger fire cleanly in prior stress phases?).

2. **Convergence rule is conceptual, not operationalised.** The Meeusen recommendation ("multiple convergent markers") is methodologically clear, but the exact aggregation logic (weighting of markers, minimum count, persistence window) requires practical experience with one's own data — not derivable from a literature study.

3. **Periodisation phase not as input:** in the build mesocycle TSB < -20 is productive; in taper TSB > +10 should be targeted. Currently `_compute_meso_load_trend` does not distinguish between build and taper phase. An extension "race_in_days < 14 → other TSB targets" would be consistent with the Coggan taper methodology.

4. **Subjective fatigue as a marker is missing.** The Meeusen consensus strongly emphasises psychometric variables (mood scores, RPE per fixed watt, motivation drop). Our framework has `athleteFeedback` (NOTE-based) — a systematic aggregation of these notes as a "subjective-fatigue trend" would be valuable, but would require an NLP pass over the NOTEs (outside the sport-science question).

5. **Recovery vs. training-block switching not modelled:** block periodisation (Issurin) alternates between accumulation (high volume) and transmutation (higher intensity, lower volume). A recovery week is NOT the same as the transition to the next blocking phase. Currently we treat both the same (1 week reduced load). Differentiation would be possible, but not mandatory.
