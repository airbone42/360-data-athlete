# Plyometrics — frequency, 48h recovery, CNS adaptation

**Created:** 2026-05-16

## TL;DR

1. **2×/week is the optimal frequency for runners.** Bell et al., Markovic & Mikulic 2010, multiple reviews: with 7-10 weeks of 2×/week plyometric training, the essential adaptation gains arrive. 3×/week brings no additional benefit and may even worsen performance temporarily.
2. **48h minimum recovery between plyo sessions** (same intensity): "High intensity sessions should have at least 48 to 72 hours of rest between sessions". High-amplitude plyo (depth jumps, hill sprints) may need 72-96h.
3. **48h block to intervals** is justifiable in the framework default: run intervals (Z4/Z5) are themselves eccentric-loading (higher pace = higher impact forces). A 48h time gap prevents cumulative CNS and tendon load.
4. **For Achilles phase-3 athletes** the conservative 48h block is particularly sensible — see [achilles-rehab-phases.md](achilles-rehab-phases.md). Only in stable phase 4 could a 24h gap be discussed.

## Findings

**Frequency optima:**
- Recreational/well-trained runners: **2×/week** is the gold standard (Markovic 2010 meta-analysis over >40 plyo studies).
- 3×/week shows in a 4-week study: weeks 2-3 performance drop, weeks 4-5 only rebound to baseline → no net added value (PMC 12515833, regional-level jumpers).
- 1×/week shows adaptation, but slower (50-70% of the 2× effects over 10 weeks).

**Recovery time per intensity level:**

| Plyo intensity | Recovery to next plyo | Examples |
|----------------|------------------------|----------|
| Low (extensive) | 24h | Pogo hops, low box jumps, skipping |
| Medium | 48h | Mid-height box jumps, hurdle sprints |
| High (intensive) | 48-72h | Depth jumps, high box jumps, bound drills |
| Maximal (shock) | 72-96h | Drop jumps from ≥60cm, all-out hill sprints |

**CNS adaptation (Bosse, Just-Fly Sports):**
> "Plyometric training drives increases in rate of force development … The nervous system needs more time to recover from training impulses, depending on the training intensity 48-96 hours."

**Practical application for a run-focused build:**
- Mon: Z4 intervals (run)
- Tue: easy run
- Wed: plyo (medium-intensity) + strength
- Thu: easy run
- Fri: easy + strides
- Sat: long run
- Sun: rest

→ Plyo 1×/week with tightly clocked quality periodisation; 2×/week possible if the second session stays low-intensity.

## Primary sources

| Author / year | Title | Publisher / link | Key quote |
|---------------|-------|------------------|-----------|
| Markovic G, Mikulic P — 2010 | Neuro-musculoskeletal and Performance Adaptations to Lower-Extremity Plyometric Training | Sports Medicine 40(10):859-895 | Foundational review for plyo adaptations + frequency recommendations |
| Sole CJ, Suchomel TJ — 2024 | Can weekly frequency of plyometric training impair strength and power? | [PMC 12515833](https://pmc.ncbi.nlm.nih.gov/articles/PMC12515833/) | "3 × week experienced performance impairments during weeks 2 and 3 … by week 4 returned to baseline levels" |
| Davies G, Riemann BL, Manske R — 2015 | Current Concepts of Plyometric Exercise | [PMC 4637913](https://pmc.ncbi.nlm.nih.gov/articles/PMC4637913/) | 48-72h recovery standard for high-intensity plyo |
| Marathon Handbook | Plyometric Exercises For Runners | [marathonhandbook.com](https://marathonhandbook.com/plyometric-exercises-for-runners/) | "One to two sessions per week is optimal for most runners, with at least 48 hours between plyometric sessions" |
| Bosse C | How often should you do Plyometric Training? | [christianbosse.com](https://christianbosse.com/how-often-should-you-do-plyometric-training/) | CNS adaptation explanation 48-96h |

## Application in framework

- **`config.example/training_paradigms.md`** plyo-frequency rule "2-3×/week for trail build" → the default 2× is well supported; 3× (during trail build) should be qualified with "only one high-intensity session, keep the other low-intensity".
- **`config.example/training_paradigms.md`** "48h spacing to intervals" is sport-scientifically justified — CNS recovery + eccentric load protection.
- **R005 validator rule** (Achilles phase 3 + plyo + hard surface = WARNING) is conservative-consistent.
- **Cross-reference** to [plyometric-progression-levels.md](plyometric-progression-levels.md) (M7) and [achilles-rehab-phases.md](achilles-rehab-phases.md) (H6).

## Open questions / Caveats

1. **Masters athletes may need longer recovery.** "Do older runners need more rest?" (RunnersConnect) — the data are consistent: yes, 25-50% more recovery time. For plyo this means: 72h instead of 48h between high-intensity sessions.
2. **Season-phase variability:** in the race-specific phase plyo can be reduced to 1×/week (reduction phase); in off-season build 2× makes sense.
3. **24h-block discussion:** with only low-intensity plyo (extensive, pogo hops) 24h would theoretically be sufficient — but is held conservatively at 48h in the framework.
