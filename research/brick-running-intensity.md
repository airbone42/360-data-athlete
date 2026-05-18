# Brick-running intensity — Z2 vs. Z1, cardiac drift, long-run sim on pre-loaded legs

**Created:** 2026-05-16

## TL;DR

1. **Brick run after the bike shows a structurally "shifted" HR response:** higher HR per pace unit than on a fresh run. Cardiac drift + neuromuscular pre-load of the quad-glute chain + glycogen pre-load are the mechanics.
2. **Differential intensity targeting:**
   - **Long-run simulation (40-60 min brick):** Z2 (aerobic base, lipid oxidation, race-specific pre-load) — pace leads, HR drift normal
   - **Recovery brick (15-25 min):** Z1 (exclusively) — recovery component, not stimulus
3. **"80/20 Triathlon" methodology (Fitzgerald):** easy mode at low volume, Z2 mode in the race-specific phase. Consistent with the polarized architecture (see [polarized-training-seiler.md](polarized-training-seiler.md)).
4. **In the framework:** training_paradigms.md already anchors the brick-intensity correction (long-run brick: Z2, not Z1). This doc provides the rationale.

## Findings

**Mechanics of the brick run:**
- During the bike phase: athlete's reservoirs charged with cardiac output + glycogen demand
- At the transition: quad/hip flexor are pre-loaded, plasma volume reduced
- Result: at the same pace 5-15 bpm higher than fresh run, pace feels "heavier"
- Cardiac drift is *normal*, not *pathological* — pace is the clean control variable, not HR

**Differential intensity approach (80/20 Triathlon, Friel, Vance):**

| Brick purpose | Duration | Intensity | Pace guidance |
|---------------|----------|-----------|---------------|
| Recovery brick | 15-25 min | Z1 only | Easy, conversational |
| Aerobic base | 30-45 min | Z1-Z2 | Z2 pace at the upper end |
| Long-run simulation | 40-60 min | Z2 | Z2 pace mid-to-upper |
| Race-pace brick | 20-30 min | Race-specific | Planned race pace |

→ The most common coaching trap: leaving all bricks at Z1 across the board → race-specific preparation is missing. The Z2 brick (40-60 min) is, evidence-based, the actual marathon-race-simulation workout in triathlon training literature.

## Primary sources

| Author / year | Title | Publisher / link | Key quote |
|---------------|-------|------------------|-----------|
| Fitzgerald M — 2014 | 80/20 Triathlon | Da Capo Press | Brick-intensity differentiation by training purpose |
| Friel J — 2009 | The Triathlete's Training Bible (4th ed) | VeloPress | Brick-run recommendations + cardiac-drift explanation |
| Vance J — 2013 | Triathlon 2.0: Data-Driven Performance Training | Human Kinetics | Power/pace-based brick steering |
| ACSM Position Stand on Endurance Training | (ongoing) | (ACSM) | Cardiac-drift mechanics with heat/pre-load |

## Application in framework

- **`config.example/training_paradigms.md`** (lines 129-134) — brick-intensity correction Z2 instead of blanket Z1 is consistent with the Fitzgerald/Friel consensus.
- **Cross-reference** to [polarized-training-seiler.md](polarized-training-seiler.md) (polarized architecture is preserved) and [cross-sport-hr-differential.md](cross-sport-hr-differential.md) (bike-vs-run HR differential also applies to brick).

## Open questions / Caveats

1. **Cardiac-drift threshold for brick:** if HR rises > 10% above the pace expectation, that's a drift signal — either lower the pace or end the brick. Consistent with the decoupling threshold (see [compliance-decoupling-thresholds.md](compliance-decoupling-thresholds.md)).
2. **Glycogen depletion on long bricks** (> 60 min bike + > 40 min run) creates extra recovery demand — these sessions are "race-day lite", not regular training.
