# Pyramidal training-intensity distribution — when instead of polarized

**Created:** 2026-05-16

## TL;DR

1. **Pyramidal = ~75% Z1 + 15-20% Z2-threshold + 5-10% Z3-high** — staircase distribution with decreasing shares at higher intensity.
2. **Polarized is VO2peak-superior** (Stöggl & Sperlich 2014, +11.7% vs. ~0% for THR), but **pyramidal has season-phase advantages in the off-season** (threshold-power build-up, LT1 shift, running economy).
3. **Switch recommendation:** Pyramidal in base phase, polarized 8-12 weeks pre-race. The CTL threshold for the switch is parametrised in the framework via `competition_plan.md`.
4. **Casado et al. 2022** show for world-class long-distance runners: pyramidal dominant in off-season, polarized in race-preparation phase.

## Findings

Pyramidal corresponds to the historically dominant TID practice (marathon training tradition, Lydiard method): lots of Z1, moderate Z2 threshold, little Z3. The threshold component builds LT1 power solidly — with repeated application the LT1 threshold shifts right, which makes Z1 pace faster at the same HR level (running-economy gain).

| Season phase | Recommended TID | Rationale |
|--------------|-----------------|-----------|
| Off-season / base | Pyramidal | LT1 shift + aerobic base |
| Race-specific phase (8-12 weeks before race) | Polarized | VO2max peak + race sharpness |
| Taper (1-3 weeks) | Reduction of both | Volume down, pace specificity |
| Recovery (1 week) | Z1 only | Recovery |

→ The framework has already implemented this logic implicitly via the CTL-threshold-based polarized/pyramidal recommendation in `training_paradigms.md` — the threshold CTL ≥ 50 (for race ≥ HM) or CTL ≥ 35 (race < HM) as trigger for polarized switch is Coggan-consistent.

## Primary sources

| Author / year | Title | Publisher / link | Key quote |
|---------------|-------|------------------|-----------|
| Stöggl T, Sperlich B — 2015 | The training intensity distribution among well-trained and elite endurance athletes | [PMC 4621419](https://pmc.ncbi.nlm.nih.gov/articles/PMC4621419/) | Cyclists 70-88% Z1, 11-22% Z2, 2-8% Z3 → pyramidal-typical |
| Casado A et al — 2022 | Periodization and Optimal Training Intensity Distribution Models in World-class Long-distance Runners | Sports Med | Pyramidal in early, polarized in race-specific |
| Treff G et al — 2019 | The Polarization-Index | Frontiers Physiology | Polarization-Index objectively quantifies TID |
| Endurometrics — n.d. | Polarized vs Pyramidal Training: Which Is Best and When? | [endurometrics.com](https://endurometrics.com/pyramidal-polarized/) | Practical switch table by season phase and athlete state |

## Application in framework

- **`config.example/training_paradigms.md`** — the pyramidal section (lines 36-49) already cites Treff 2019 + Casado 2022 as sources; this doc provides the persisted anchor.
- Cross-reference to [polarized-training-seiler.md](polarized-training-seiler.md) and [recovery-week-triggers.md](recovery-week-triggers.md) (season-phase switch logic).
- **CTL-threshold switch** (CTL ≥ 50 for ≥ HM, ≥ 35 for < HM) remains correct — Coggan consistency with pyramidal/polarized season recommendation.

## Open questions / Caveats

1. **Z2-threshold window in pyramidal** is broad (15-20%). For masters athletes the lower half (15%) is sensible due to slower recovery.
2. **Polarization-Index as an operationalised metric** would be a code extension in the framework — see caveat in [polarized-training-seiler.md](polarized-training-seiler.md).
