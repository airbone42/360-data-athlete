# Downhill running — eccentric damage, DOMS timeline, taper recommendation

**Created:** 2026-05-16

## TL;DR

1. **Downhill running produces extreme eccentric muscle damage** (EIMD = exercise-induced muscle damage), primarily in quadriceps and calf muscles. Mechanics: muscle as "shock absorber", rapid extension→compression tears muscle fibres.
2. **DOMS peak at 48h, strength loss in parallel.** Full recovery of all muscle-damage markers: ~4 days. In untrained athletes or steep downhill sections: up to 7+ days.
3. **Performance limiter in trail races:** "Muscle damage is thus proposed as a main performance-limiting factor in mountain running." Completing race downhill sections successfully requires prior eccentric adaptation.
4. **Taper recommendation:** cut the downhill block in the **last 7-10 days** before race. 4-day DOMS recovery + safety margin. On steep trail downhill loads, rather 10 days.

## Findings

**Mechanism of downhill EIMD:**
- During ground contact, muscles act as shock absorbers
- On steep gradients: extreme eccentric forces (muscle lengthens under load)
- Across the braking phase: quadriceps + calf muscles strain at maximum protective tension
- Repeated exposure → microtrauma + DOMS

> "Downhill running involves a particularly high intensity of eccentric contractions because of the muscle tension required to move fast on steep gradients without falling. Muscles essentially act as shock-absorbing springs, going from extension to compression very rapidly. This can cause extreme skeletal muscle damage." (Trail Runner Magazine, based on Hoffman 2014 + Easthope 2010)

**Timeline (Hoffman, Easthope, Vernillo et al. 2017 Sports Med):**

| Marker | Peak | Recovery |
|--------|------|----------|
| Maximum voluntary force | -20 to -30% immediately | 3-4 days |
| DOMS / subjective soreness | 48h post | 4-7 days |
| CK (creatine kinase) | 24-48h | 5-7 days |
| Inflammatory markers | 24h | 2-3 days |

**Repeated-bout effect:**
Regular downhill intervals (e.g. 1×/week short downhill reps) reduce EIMD on later loads by 30-50%. "Regularly undertaking DR intervals and adopting a more terrestrial gait pattern appears to soften strength loss and muscle damage response to DR" — so downhill practice belongs in the trail build, but NOT in the last 7-10 days pre-race.

**Practice recommendation (Vernillo et al., MDPI Sports 2024):**
- Trail build phase: 1×/week short downhill reps (4-6 × 30-60s @ moderate downhill)
- 8-12 weeks pre-race: downhill intervals as regular stimulus
- Race-specific phase 2-4 weeks pre-race: reduce volume but maintain downhill practice
- **Taper week (last 7 days):** cut the downhill block entirely (DOMS-recovery safety margin)

## Primary sources

| Author / year | Title | Publisher / link | Key quote |
|---------------|-------|------------------|-----------|
| Vernillo G et al — 2017 | Biomechanics and Physiology of Uphill and Downhill Running | Sports Medicine 47:615-629 | EIMD mechanics + eccentric-adaptation logic |
| Vernillo G et al — 2020 | Downhill Running: What Are The Effects and How Can We Adapt? A Narrative Review | [PMC 7674385](https://pmc.ncbi.nlm.nih.gov/articles/PMC7674385/) | Comprehensive review on downhill adaptation |
| Vernillo G et al — 2024 | Downhill running increases markers of muscle damage and impairs the maximal voluntary force production | [PMC 11129977](https://pmc.ncbi.nlm.nih.gov/articles/PMC11129977/) | Quantitative evidence for DOMS timeline |
| MDPI Sports 2024 | Downhill Running-Induced Muscle Damage in Trail Runners | [MDPI](https://www.mdpi.com/2075-4663/14/1/12) | Repeated-bout-effect data |
| Trail Runner Magazine | Strength Train For Better Downhill Running | [trailrunnermag.com](https://www.trailrunnermag.com/training/trail-tips-training/last-longer-downhills-training-eccentric-muscle-contractions/) | Practice overview for trail trainers |

## Application in framework

- **`config.example/training_paradigms.md`** "trail tapering: cut downhill block in last 7d" → refined with Vernillo 2020/2024 source anchors. For steep trail profiles (race section with > 10% downhill over multiple km) extend to 10 days.
- **Trail build recommendation:** 1×/week downhill reps in the 8-12-week race-specific phase as a repeated-bout-effect anchor.
- **Cross-reference** to [hill-repeats.md](hill-repeats.md) (uphill counterpart) and [doms-peak-timing.md](doms-peak-timing.md) (M14, generic DOMS timeline).

## Open questions / Caveats

1. **Volume ceiling for downhill intervals** should be kept conservative — 4-6 reps of 30-60s with full recovery between reps. More volume is not more productive, because EIMD scales non-linearly with volume.
2. **For trail athletes with Achilles phase < 4** downhill practice is contraindicated due to increased eccentric calf load. Only introduce in stable phase 4.
3. **Race-day pacing for downhill** should be more conservative than uphill — eccentric damage accumulates over race duration and limits the last 30% of the race.
