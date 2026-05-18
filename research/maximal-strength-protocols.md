# Maximal-strength protocols — 4×4-6 @ 80-85% 1RM standard

**Created:** 2026-05-16

## TL;DR

1. **Classical maximal-strength range: 1-5 reps @ 80-100% 1RM.** Our framework default 4×4-6 @ 80-85% 1RM @ RPE 7-8 sits at the lower end of the heavy-strength range and the upper end of the hypertrophy/strength overlap — a deliberate compromise for masters athletes without a powerlifting goal.
2. **NSCA consensus:** "Training heavy with a weight that can only be done for 6 or less reps (≥ 85% 1RM) for 2-6 sets resting 2-5 minutes between each set is a standard recommendation for maximal strength development."
3. **Powerlifter minimum dose** (Mattocks et al. 2017, Frontiers 2021): 3-6 working sets of 1-5 reps per week per lift, at 80% 1RM, RPE 7.5-9.5, 6-12 weeks → robust 1RM gain.
4. **Rests 90-180s:** conservative middle ground. True strength optima are 2-5 min rest (complete PCr resynthesis). 90s is more in the hypertrophy band; 180s approaches the strength optimum.

## Findings

**Schoenfeld 2021 (Re-Examination of the Repetition Continuum):**

| Endpoint | Reps | %1RM | Sets | Rest | RPE |
|----------|------|------|------|------|-----|
| Strength (1RM) | 1-5 | 80-100% | 2-6 | 2-5 min | 8-9 |
| Hypertrophy | 6-12 | 65-85% | 3-6 | 60-120s | 7-9 |
| Local endurance | 15+ | < 60% | 2-3 | 30-60s | 6-8 |

**Important nuance:** Schoenfeld shows that hypertrophy is achievable across a broad rep range (up to 30 reps) when training close to failure. Maximal-strength adaptation is more tightly tied to low reps — neural factors (recruitment, rate of force development) profit primarily from reps ≤ 5.

**Our framework default 4×4-6 @ 80-85% RPE 7-8:**
- Reps 4-6 → at the strength/hypertrophy boundary
- 80-85% 1RM → classic strength band
- RPE 7-8 → 2-3 reps in reserve, not to failure
- Rest 90-180s → middle ground

→ Consistent with "strength-hypertrophy hybrid" for non-powerlifters with a sport background (runners, ninja athletes). Pure powerlifters would do 3×3 @ 90%+; pure bodybuilders 4×10 @ 70%. Our mix is optimised for power-endurance transfer.

**Mattocks et al. 2017 / Androulakis-Korakakis et al. 2021 (minimum effective dose):**
> "Powerlifters can perform ~3-6 working sets of 1-5 repetitions each week, with these sets spread across 1-3 sessions per week per powerlift, using loads above 80% 1RM at a Rate of Perceived Exertion (RPE) of 7.5-9.5 for 6-12 weeks and expect to gain strength."

→ The minimum effective dose is surprisingly low. For our athlete (maximal-strength block for pull/grip/leg periodisation), 1 session/week per pillar is sufficient if the volume anchors fit.

**Zatsiorsky classic ("Science and Practice of Strength Training"):** maximal strength requires "maximum tension" — that is: heavy loads (≥ 80% 1RM) or dynamic load (velocity close to maximum). Both trigger maximum motor-unit recruitment. Our 80-85% band satisfies the maximum-tension component.

## Primary sources

| Author / year | Title | Publisher / link | Key quote |
|---------------|-------|------------------|-----------|
| Schoenfeld BJ et al — 2021 | Loading Recommendations for Muscle Strength, Hypertrophy, and Local Endurance: A Re-Examination of the Repetition Continuum | [PMC 7927075](https://pmc.ncbi.nlm.nih.gov/articles/PMC7927075/) | Strength: 1-5 reps @ 80-100% 1RM; hypertrophy: 6-12 reps @ 65-85% |
| Androulakis-Korakakis P et al — 2021 | The Minimum Effective Training Dose Required for 1RM Strength in Powerlifters | [PMC 8435792](https://pmc.ncbi.nlm.nih.gov/articles/PMC8435792/) | 3-6 working sets × 1-5 reps × 80%+ × RPE 7.5-9.5 as minimum 1RM-effective dose |
| Zatsiorsky VM, Kraemer WJ — 2006 | Science and Practice of Strength Training (2nd ed) | Human Kinetics | Maximum tension / maximum effort as foundation principles |
| Schoenfeld BJ — 2017 | Strength and Hypertrophy Adaptations Between Low- vs. High-Load Resistance Training | [PubMed 28834797](https://pubmed.ncbi.nlm.nih.gov/28834797/) | Hypertrophy achievable across broad rep range, strength more tightly bound |
| Bosse C — n.d. | The Holy Grail of Strength Training | [christianbosse.com](https://christianbosse.com/the-holy-grail-of-strength-training-how-many-reps-how-many-sets/) | Coach practice overview on sets/reps |
| NSCA Training Load Chart | (table) | [nsca.com](https://www.nsca.com/contentassets/61d813865e264c6e852cadfe247eae52/nsca_training_load_chart.pdf) | RM-to-%1RM table |

## Application in framework

- **`config.example/exercise_progressions.md`** "Maximal-strength block 4×4-6 @ 80-85% 1RM, RPE 7-8, 90-180s rest" — this doc provides the source anchor (Schoenfeld 2021, Androulakis-Korakakis 2021, Zatsiorsky 2006).
- **Cross-reference** to [hypertrophy-rep-ranges.md](hypertrophy-rep-ranges.md) (M9) for the hypertrophy variant.

## Open questions / Caveats

1. **Masters athletes:** recovery times may be longer (72h between heavy strength sessions on the same pillar). RPE 7-8 instead of 9-9.5 is conservative-sensible because of a narrower injury margin.
2. **Pull/grip vs. leg-strength block:** leg strength interacts with run volume (see [concurrent-training-interference.md](concurrent-training-interference.md), M5). Pull/grip is less interference-prone.
3. **Velocity-based training (VBT)** is not used in our framework — would be a more objective RPE alternative but requires hardware (encoder).
