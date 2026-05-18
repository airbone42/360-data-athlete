# Hypertrophy rep range — Schoenfeld's sweet spot and the 15-rep validator

**Created:** 2026-05-16

## TL;DR

1. **Hypertrophy sweet spot: 6-12 reps @ 65-85% 1RM** is the classic ACSM/NSCA range. Schoenfeld 2021 shows: hypertrophy is achievable across a broader rep range (up to 30 reps) when training near failure — but 6-12 remains the practical sweet spot for the mechanical-tension + metabolic-stress combo.
2. **Our R001 validator threshold of 15 reps** is conservative-sensible as an hypertrophy upper bound. More reps progressively move into the "local endurance" range (Schoenfeld 2021: > 15 reps → Schoenfeld calls this "local muscular endurance").
3. **Volume stimulus for hypertrophy:** 10+ sets per muscle group/week (Schoenfeld meta-analysis) as a minimum anchor; 12-20 sets as the evidence-based optimum for trained men.
4. **Mechanical tension > metabolic stress as primary trigger.** "Mechanical tension is one of the main mechanisms inducing muscle hypertrophy by leading to signal transduction and increasing muscle protein synthesis."

## Findings

**Schoenfeld 2021 rep-continuum re-examination:**

| Endpoint | Reps | %1RM | Primary mechanism |
|----------|------|------|-------------------|
| Strength | 1-5 | 80-100% | Neural (motor unit recruitment, RFD) |
| Hypertrophy (sweet spot) | 6-12 | 65-85% | Mechanical tension + metabolic stress |
| Hypertrophy (high-rep) | 13-30 | 30-65% | Metabolic stress dominant, mech-tension lower |
| Local endurance | 30+ | < 30% | Mitochondria, capillaries, buffering |

→ Provided proximity to failure, hypertrophy can be achieved across 6-30 reps. But 6-12 is the **time-efficient sweet spot** — same effect with less volume accumulation.

**Schoenfeld volume meta-analysis:**
- Minimum volume for hypertrophy: **10 sets/muscle/week** as anchor
- Optimum for trained athletes: **12-20 sets/muscle/week**
- Dose-response plateau around ~25-30 sets — beyond that, more harm than benefit

**Our R001 validator rule (reps > 15 → ERROR):**
- Scientifically justifiable as "crossing into local endurance"
- But: 13-15 reps would still be within the hypertrophy continuum, not at endurance
- → threshold 15 is a conservative-clean hypertrophy upper bound, avoids shift to pure endurance adaptation
- Clarification in the validator header comment: "> 15 reps: mechanical-tension reduction, primarily metabolic/endurance adaptation — not target-aligned for a hypertrophy goal"

## Primary sources

| Author / year | Title | Publisher / link | Key quote |
|---------------|-------|------------------|-----------|
| Schoenfeld BJ et al — 2021 | Loading Recommendations for Muscle Strength, Hypertrophy, and Local Endurance: A Re-Examination of the Repetition Continuum | [PMC 7927075](https://pmc.ncbi.nlm.nih.gov/articles/PMC7927075/) | Rep-continuum table strength/hypertrophy/endurance |
| Schoenfeld BJ, Contreras B et al — 2017 | Strength and Hypertrophy Adaptations Between Low- vs. High-Load Resistance Training: A Systematic Review and Meta-analysis | [PubMed 28834797](https://pubmed.ncbi.nlm.nih.gov/28834797/) | Hypertrophy achievable across broad rep range when close to failure |
| Schoenfeld BJ et al — 2017 | Evidence-Based Guidelines for Resistance Training Volume to Maximize Muscle Hypertrophy | [Schoenfeld](https://elementssystem.com/wp-content/uploads/2018/08/Schoenfeld-volumen-review.pdf) | 10+ sets/muscle/week as hypertrophy minimum, 12-20 as optimum |
| Stronger by Science (Nuckols G) | The "Hypertrophy Rep Range" — Fact or Fiction? | [strongerbyscience.com](https://www.strongerbyscience.com/hypertrophy-range-fact-fiction/) | Practice overview of the sweet-spot debate |

## Application in framework

- **`framework/scripts/validate_plan.py` R001** — extend the header comment: "> 15 reps leaves the hypertrophy sweet spot. Source: `framework/research/hypertrophy-rep-ranges.md`."
- **`config.example/exercise_progressions.md`** — for hypertrophy-focused exercises: recommendation 6-12 reps @ 65-85% 1RM, 3-6 sets per week per muscle group.
- **Cross-reference** to [maximal-strength-protocols.md](maximal-strength-protocols.md) (M8) for the strength variant.

## Open questions / Caveats

1. **15 vs. 20 as validator threshold:** some sources see the transition to endurance only at 20 reps. A relaxation of the R001 threshold to 18-20 would be defensible — currently 15 is the conservative-safe choice.
2. **Hypertrophy volume for masters athletes:** Schoenfeld's data are primarily from trained men 20-40 y. Masters may require higher volumes (15-25 sets/muscle) for the same stimulus due to anabolic resistance.
3. **Endurance-athlete-specific hypertrophy need:** runners/triathletes mostly want *functional* hypertrophy, not maximum cross-section. Lower volume (3-6 sets/muscle) is often sufficient here.
