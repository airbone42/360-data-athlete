# MAP — Maximum Aerobic Power, ramp-test protocols, FTP relationship

**Created:** 2026-05-16

---

## TL;DR

1. **MAP (Maximum Aerobic Power)** is the last fully completed 1-min power step of a ramp test to exhaustion. It correlates closely with the power output at the VO2max plateau and is the standard anchor for VO2max-stimulus intensity.

2. **Standard ramp protocols by population:**
   - Non-elite men: **25 W/min** (standard)
   - Elite men: 20 W/min
   - All women: 15 W/min
   - Start typically at 100 W, 5 W steps every 12s (non-elite) or 20s (women) for a smooth ramp
   - Test duration: 10-20 min, until cadence drops below 70 rpm or the athlete signals capacity reached

3. **MAP-to-FTP ratio** is **not** fixed at 75% — the empirical distribution lies at **72-77% of MAP** for 97% of athletes (CycleCoach dataset). The frequently cited 75% convention (Zwift, TrainerRoad) is a simplification; individually it must be validated whether the athlete lies in the 72%, 75% or 77% band.

4. **MAP-to-VO2max formula** (Hawley-Noakes): `VO2max (L/min) = 0.01141 × MAP (W) + 0.435`. Delivers for trained cyclists an estimate with ~5% error — no replacement for lab VO2max, but field-capable.

5. **30/15 Rønnestad intensity in MAP terms:** 100% MAP for 30s on, 50% MAP for 15s off. In FTP terms this corresponds, depending on the athlete, to **130-138% FTP** (for the 72% ratio) or **130-133% FTP** (for the 77% ratio). → The old framework rule "130-145% FTP" for 30/15 is the upper half of this range and corresponds to "intensified" 30/15 — the Frontiers 2024 study shows: that reduces time-above-90% VO2max instead of raising it.

---

## Question / Trigger

In the doc [`vo2max-short-intervals.md`](vo2max-short-intervals.md) the core insight was captured:

> "MAP definition in practice: MAP is the lowest power at which VO2max is reached — usually measured via a stepped test ('ramp test') as the 1-min or 5-min peak power. In trained cyclists, MAP is typically 105-120% FTP."

What is missing in the doc:
- What does the **concrete** ramp test that measures MAP look like? Ramp rate? Start watts? Duration?
- How validated is the **MAP-to-FTP conversion** (range, individual variation)?
- How can MAP be estimated **without a lab test** (field tests)?
- What does the **MAP-to-VO2max conversion** look like?

Questions:
1. Which ramp-test protocols are standard?
2. Which MAP-FTP ratio range is empirically documented?
3. Which formulas deliver VO2max from MAP?
4. How should the athlete measure his MAP value cleanly when no lab is available?

---

## Findings

### 1. MAP definition and test protocol

**MAP (Maximum Aerobic Power)** is the highest 1-min power step an athlete can fully complete in a ramp test to exhaustion. It represents the power output at which VO2max is just reached (Hawley & Noakes 1992).

**Standard ramp-test protocol:**

| Population | Ramp rate | Smooth variant |
|------------|-----------|-----------------|
| Non-elite men | **25 W/min** | 5 W every 12s |
| Elite men | 20 W/min | 5 W every 15s |
| All women | 15 W/min | 5 W every 20s |

**Start:** typically 100 W (warm-up beforehand), step is automatically raised until:
- Athlete can no longer hold cadence (< 70 rpm)
- Athlete signals "cap" and stops
- HR plateau without further rise

**Duration range:** 10-20 min main set, the ideal sweet spot is 12-15 min test duration.

**Source:** Hawley JA, Noakes TD (1992). "Peak power output predicts maximal oxygen uptake and performance time in trained cyclists." Eur J Appl Physiol. Plus CycleCoach.com practice operationalisation → [cyclecoach.com](https://www.cyclecoach.com/blog/2020/2/2/is-the-map-ramp-test-a-valid-estimator-of-ftp)

### 2. MAP-to-VO2max conversion

**Hawley-Noakes formula (1992):**
```
VO2max (L/min) = 0.01141 × MAP (W) + 0.435
VO2max (ml/min/kg) = [VO2max (L/min) × 1000] / body weight (kg)
```

**Alternative (often cited):**
```
VO2max (L/min) = 0.44 + (0.014 × MAP)
```

Example calculation (70 kg, MAP 320 W):
- Hawley-Noakes: VO2max = 0.01141 × 320 + 0.435 = 4.09 L/min = 58.4 ml/min/kg
- Alt formula: VO2max = 0.44 + 0.014 × 320 = 4.92 L/min = 70.3 ml/min/kg

The two formulas diverge considerably — both are field-capable, but neither replaces lab spirometry. Hawley-Noakes is the academically tested standard formula and should be used as default.

### 3. MAP-to-FTP ratio

The frequently cited "75% rule" (Zwift, TrainerRoad) is a **simplification**. Empirically:

> "riders could maintain about 70ish percent of their MAP for 1 hour" (based on 1990s-2000s data)
> "over 97% of the people … their best ~1 hour power was always in the region of 72 - 77%" (CycleCoach data)

**Individual variation:**
- **Sprinter / highly anaerobic phenotypes:** closer to 72% (FTP is relatively lower than MAP)
- **Diesel / highly aerobic phenotypes:** closer to 77% (FTP uses more of the MAP level)

→ The CycleCoach author warns explicitly: "Just 10W and it's too much for me … Trying to use 270W as my FTP just results in me blowing up mid-session." That means the 75% estimate can in individual cases be ~3-5% too high — at a 360 W MAP, up to 11 W miscalculation.

**Validation strategy:**
- Ramp test delivers MAP
- 20-min FTP test (separate day) delivers true FTP
- Individual ratio = FTP / MAP is documented athlete-specifically
- Future ramp tests can then use the individual ratio

### 4. Application to the 30/15 Rønnestad

Original protocol **Rønnestad 2013, 2015, 2020:** "MAP as exercise intensity, … recovery period being 50% of the work duration at intensity equal to 50% of MAP."

→ 30s on @ **100% MAP**, 15s off @ **50% MAP**.

For an athlete with FTP 280 W and individual FTP/MAP = 0.75 (typical):
- MAP = 280 / 0.75 = **373 W**
- 30s on @ 373 W = 133% FTP
- 15s off @ 187 W = 67% FTP

For an athlete with FTP/MAP = 0.72 (anaerobic-leaning):
- MAP = 280 / 0.72 = **389 W**
- 30s on @ 389 W = 139% FTP
- 15s off @ 194 W = 69% FTP

For an athlete with FTP/MAP = 0.77 (diesel):
- MAP = 280 / 0.77 = **364 W**
- 30s on @ 364 W = 130% FTP
- 15s off @ 182 W = 65% FTP

→ **The correct 30/15 watt prescription depends on the individual FTP/MAP ratio** and lies in the 130-140% FTP range for 30s on. The framework standard should be **130% FTP as a conservative default**, with individual upward calibration when FTP/MAP < 0.75 is documented.

**Reconciling with `vo2max-short-intervals.md`:** that doc reads "105-120% FTP" as the typical MAP range — that corresponds to FTP/MAP = 0.83-0.95. This range is **higher** than the empirical data referenced here (72-77%). Possible explanations:
- "Trained cyclists" in the Hawley-Noakes line vs. "well-trained" in the Rønnestad line are differently defined
- "MAP" was historically defined in some studies as 5-min MMP instead of 1-min ramp load → that yields higher FTP/MAP values (closer to 100%)
- The Rønnestad practice recommendation "105-120% FTP" could serve as a safer middle ground that works for a broad athlete population

**Update to the vo2max-short-intervals.md statement:** "MAP ≈ 1-min peak ramp is typically 130-140% FTP; 5-min peak (5MMP) is typically 105-120% FTP." The two definitions should be explicitly separated — Rønnestad refers to the 1-min peak (= classical MAP), not to 5MMP.

### 5. Field-test alternatives without an ergometer

If no smart trainer with a fixed watt target is available:

- **8-min MMP test** as FTP proxy: maximum 8-min effort, output × 0.9 = FTP (acceptable field estimation)
- **5-min peak power** as MAP proxy (alternative to ramp): maximum 5-min effort, output × 1.07 ≈ 1-min ramp MAP (CycleCoach recommends this conversion)
- **20-min FTP test** as "gold-standard" field test: 20-min time trial × 0.95 = FTP (Coggan methodology)

### 6. Limits of the ramp test

> "Ramp tests can be less accurate depending on your physiology, specifically for riders with a higher anaerobic to aerobic power balance who may have their FTP overstated by a ramp test."

→ Sprinter phenotypes can "overshoot" in a ramp-test endgame with anaerobic reserve, leading to MAP overestimation and thus FTP overestimation. On repetition of the same reps in training then unsustainable — exactly the pattern of a documented 1-min effort peak from real application that was set too high as a 30/15 prescription.

**Consequence:** MAP values should be validated against practice reps. If 30/15 at the MAP prescription is unsustainable, the MAP estimate is too high or the individual FTP/MAP ratio is lower than assumed.

---

## Primary sources

| Author / year | Title | Publisher / link | Key quote |
|---------------|-------|------------------|-----------|
| Hawley JA, Noakes TD — 1992 | Peak power output predicts maximal oxygen uptake and performance time in trained cyclists | Eur J Appl Physiol 65(1):79-83 | `VO2max (L/min) = 0.01141 × MAP (W) + 0.435` |
| Rønnestad BR, Hansen J — 2013 | Optimizing Interval Training at Power Output Associated With Peak Oxygen Uptake in Well-Trained Cyclists | [PubMed 23942167](https://pubmed.ncbi.nlm.nih.gov/23942167/) | "MAP as exercise intensity, recovery period being 50% of the work duration at intensity equal to 50% of MAP" |
| Stern R / CycleCoach — 2020 | MAP Ramp Test: Can It Accurately Estimate FTP? | [cyclecoach.com](https://www.cyclecoach.com/blog/2020/2/2/is-the-map-ramp-test-a-valid-estimator-of-ftp) | "over 97% of the people … their best ~1 hour power was always in the region of 72 - 77%" of MAP |
| TrainerRoad — 2019 | Ramp Test Makes FTP Testing More Efficient and Less Stressful | [trainerroad.com](https://www.trainerroad.com/blog/new-ramp-test-makes-ftp-testing-more-efficient-and-less-stressful/) | FTP = 75% × highest 1-min ramp power as default conversion |
| Chris Carmichael — 2019 | FTP Tests: How to perform 20-Minute, 8-Minute, and Ramp Tests | [trainright.com](https://trainright.com/ftp-tests-how-to-perform-20-minute-8-minute-and-ramp-tests/) | Comparison of the three field tests, accuracy ranges |
| SemiPro Cycling Podcast | Maximal Aerobic Power (MAP) Testing Explained | [semiprocycling.com](https://www.semiprocycling.com/podcast/map) | Coach practice overview on ramp-test application |

---

## Application in framework

### What is confirmed

- **MAP as VO2max intensity anchor** (in `vo2max-short-intervals.md`) is conceptually correct.
- **Ramp test as standard MAP measurement method** is evidence-based.
- **`config/training_paradigms.md` "MAP range correction"** (30/15 reps at MAP, not 130-145% FTP intensified) is sport-scientifically well grounded — see `vo2max-short-intervals.md` + this doc as supplementary anchors.

### What should be changed / refined

1. **`framework/config.example/training_paradigms.md`** — clarification update on the 30/15 intensity:
   - Clear distinction between **1-min ramp MAP** (Rønnestad anchor, typically 130-140% FTP) vs. **5-min MMP** (typically 105-120% FTP) — the two are not identical
   - Recommendation: determine athlete-specific FTP/MAP ratio from ramp test + FTP test, then document as a constant in `athlete_status.md`
   - Reference this doc as methodology anchor
2. **`framework/config.example/zone_validation_protocol.md`** — new section "MAP test protocol":
   - Ramp-rate table by population (15/20/25 W/min)
   - 5 W steps every 12-20s for smooth ramp
   - Start at 100 W, warm-up 10 min beforehand
   - Abort criteria (cadence < 70 rpm, RPE 10/10, HR plateau)
   - Hawley-Noakes VO2max formula
3. **`framework/research/vo2max-short-intervals.md`** — add cross-reference to this doc (in the application-in-framework section), clarification 1-min MAP vs. 5MMP.

### What stays unchanged

- **FTP as primary anchor construct** for power zones stays — MAP is a special anchor for VO2max stimulus sessions (30/15, 4×4 uphill), not a universal replacement for FTP-based zones.
- **20-min FTP test as standard FTP determination** stays — the ramp test is a supplement, not a replacement, because the FTP estimation via 75% × MAP is individually too inaccurate.

---

## Open questions / Caveats

1. **Athlete-specific MAP value** must be individually measured — without a current measurement, the 30/15 watt prescriptions are not cleanly calibrated. A ramp test is the natural way there; belongs in athlete configuration as an action item.

2. **5MMP vs. 1-min ramp MAP confusion in the literature** is persistent. Many coach sources (TrainingPeaks, Spare Cycles) use "MAP" synonymously with 5MMP — which does not strictly match the Rønnestad definition. When adopting power-anchor recommendations from sources, the MAP definition must always be checked.

3. **Ramp-rate sensitivity** is not trivial — the same athlete delivers different "MAP" values at 20 W/min vs. 25 W/min ramp because glycolytic participation is different. A standardised 25 W/min ramp for our athlete and consistent repetition is mandatory.

4. **Indoor vs. outdoor MAP:** indoor ramp test is the standard because watt control is exact; outdoor field tests (5-min hill peak) have higher variability (wind, gradient fluctuation). Indoor smart trainer is the clean measurement environment.

5. **VO2max estimation from MAP is not clinically usable** — the Hawley-Noakes formula is a rough correlation. When precise VO2max values are needed (e.g. for DFA-α1 validation or training-zone definition via vVO2max), lab spirometry is the only reliable test.
