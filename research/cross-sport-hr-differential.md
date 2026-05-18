# Cross-sport HR differential — Run vs. Bike vs. Swim

**Trigger:** the framework carries a mandatory section "Sport-specific HR-zone application (MANDATORY)" in CLAUDE.md, introduced after a documented drift incident from real application — the coach answered an HR-pacing question on the bike with run HR-zone targets, and the athlete reported back that the prescribed HR range was unreachable at the prescribed watt target (legs as the limiter, not HR), revealing an unhonoured cross-sport HR differential. The underlying sport-physiological statement "bike HRmax several bpm below run HRmax" was documented as an assumption in the athlete-specific `athlete_status.md`, but without a generic sport-science source. This doc fixes the generic statement.

---

## TL;DR

1. **Run HRmax > Bike HRmax > Swim HRmax** is physiologically consistently documented. Typical differentials for triathletes and endurance athletes:
   - **Run vs. Bike: 5-10 bpm run higher** (Friel consensus, 220 Triathlon, Slowtwitch practice majority view)
   - **Run vs. Swim: 10-15 bpm run higher** (swimming + horizontal + non-weight-bearing additionally reduces HR drive)
2. **Mechanisms** are multifactorial and well documented (Bijker et al. 2002, Millet et al. 2009):
   - **Muscle-mass recruitment:** running engages large trunk and leg drive muscles, forcing higher stroke volume + higher HR
   - **Postural component:** upright position (run) vs. bent position (bike) — lower preload in the bike position → higher stroke volume compensates → lower HR
   - **Eccentric loading:** running has eccentric-concentric cycles with higher metabolic cost; cycling is predominantly concentric → lower O2 demand per watt of output
3. **Sport-specific zones are mandatory.** Friel, 80/20 Endurance, all relevant triathlon coaches agree: separate LTHR tests per sport, separate zone tables. **Applying run zones on the bike = athlete systematically trains in too high a zone.**
4. **The size of the differential is individually variable.** 5-10 bpm is the median; for triathletes with long bike experience the gap can be smaller (3-5 bpm), for runners with little bike volume larger (10-15 bpm). Empirical validation via actual watt-vs-HR data is therefore mandatory.

---

## Question / Trigger

CLAUDE.md introduced a hard mandatory section after a drift incident in real application:

> **Drift incident pattern:** the coach answered a Rønnestad 30/15 HR-pacing question with the run-zone sweet spot for "end of set 1", without consulting the bike-HR correction section that documents the athlete's cross-sport HRmax differential. The run zone lies on the bike in upper Z5 instead of the intended bike Z4-mid; the athlete reports the mismatch empirically (HR does not reach the target because the legs limit before the HR).

The statement "bike HRmax several bpm below run HRmax" in `athlete_status.md` was a heuristic without a generic anchor. Questions:

1. How large is the typical HRmax differential run-vs-bike in the literature?
2. Which physiological mechanisms explain the differential?
3. How large are the individual fluctuations?
4. What practice recommendations for zone setup exist for multi-sport athletes?

---

## Findings

### 1. Differential magnitudes

**Run vs. Bike HRmax:**
- **5-10 bpm run higher** (majority consensus from Runworks, Slowtwitch, 220 Triathlon, NYCC, Joe Friel, 80/20 Endurance)
- "It is reasonable to subtract 7 to 10 bpm from a recently tested running maximum heart rate to estimate cycling maximum heart rate" (Slowtwitch forum consensus)
- For triathletes: up to 10-15 bpm has been documented (Quora practice examples from triathlon coaching, valid with longer recovery differences)

**LTHR Run vs. Bike:**
- "Your cycling lactate threshold heart rate will be 5-10 bpm lower than your running lactate threshold heart rate because of the postural difference." (220 Triathlon Magazine)
- Friel consensus: separate 30-min time-trial tests per sport, individual LTHR per sport → individual HR-zone tables

**Run vs. Swim HRmax:**
- 10-15 bpm run higher (horizontal position + non-weight-bearing clearly reduces HR drive)
- Swimming: lowest HRmax of the three disciplines — 220 Triathlon: "Swimming, a horizontal, non-weight bearing activity, will have the lowest heart rate maximum of the three disciplines."

### 2. Physiological mechanisms

**Millet GP, Vleck VE, Bentley DJ (2009) — Sports Medicine Review** (PubMed 19290675) provides the methodologically clean overview:

> "VO2max is specific to the exercise modality. … the differences stem from the relative adaptation of cardiac output influencing VO2max and also the recruitment of muscle mass in combination with the oxidative capacity."
> "Heart rate is different between the two activities both for maximal and submaximal intensities."
> "Ventilation is more impaired in cycling than in running."
> "Central fatigue and decrease in maximal strength are more important after prolonged exercise in running than in cycling."

**Core mechanisms:**

(a) **Muscle-mass recruitment:** running activates trunk + large leg-muscle groups in concentric-eccentric cycles → higher O2 demand per output unit → higher HR. Cycling primarily recruits the quadriceps + gluteals in concentric cycles with more constant output patterns → lower relative HR per power output.

(b) **Posture and venous return:** in the bike position (bent, seated) the height difference between heart and working muscles is smaller → better venous return → higher stroke volume → HR can stay lower at the same cardiac output. With running upright the hydrostatic-pressure effect is larger → lower stroke volume → higher HR compensation.

(c) **Eccentric loading:** running has ground-contact impacts with eccentric quad loading at every step — this raises the metabolic effort structurally. Cycling has almost no eccentric component (except braking / downhill).

(d) **Cooling and ventilation:** cycling with airstream allows better heat dissipation → lower cardiac stress from thermoregulation. Running typically generates higher core temperature at the same metabolic load → higher HR through the thermoregulation component.

### 3. Individual variation

The cited sources are consistent in a range **5-15 bpm**, but:

- **Sport background matters:** pure runners with little bike volume often show the upper range (10-15 bpm) — their bike aerobic adaptation is more limited, they can use the bike system less far. Triathletes with long bike experience show smaller gaps (5-8 bpm).
- **Age & training state matter:** masters athletes tend to show smaller absolute HRmax values, but the relative differential remains similar.
- **Bike setup matters:** an aggressive TT position reduces lung compliance and can lower HRmax further. An upright endurance position is closer to run values.

**Empirical validation is therefore mandatory** — a generic "bike HRmax = run HRmax − 8" should be treated as a starting value and validated with one's own watt-vs-HR data (e.g. on an all-out 5-min effort on the bike HRmax should almost be reached).

### 4. Practice recommendation — separate tests, separate zones

**Joe Friel (triathlon-coaching bible level, "Quick Guide to Setting Zones"):**
- 30-min time trial per sport
- Last 20 min are the HR-anchor phase
- LTHR = avg HR of the last 20 min
- Calculate zones from there (Friel table: Z1 < 85% LTHR, Z2 85-89%, Z3 90-94%, Z4 95-99%, Z5a 100-102%, Z5b 103-105%, Z5c > 106%)
- **Separate tables per sport.**

**80/20 Endurance:** "Lactate Threshold Heart Rate is slightly different in running than it is in other aerobic activities, so if you choose to cross-train, you'll need to do separate tests in each activity."

**Source:** Friel J — "A Quick Guide to Setting Zones" → [joefrieltraining.com](https://joefrieltraining.com/a-quick-guide-to-setting-zones/). Plus 80/20 Endurance "Mastering Intensity Guidelines for 80/20 Triathlon" → [8020endurance.com](https://www.8020endurance.com/intensity-guidelines-for-8020-triathlon/)

---

## Primary sources

| Author / year | Title | Publisher / link | Key quote |
|---------------|-------|------------------|-----------|
| Millet GP, Vleck VE, Bentley DJ — 2009 | Physiological differences between cycling and running: Lessons from triathletes | [PubMed 19290675](https://pubmed.ncbi.nlm.nih.gov/19290675/) | "VO2max is specific to the exercise modality. … the differences stem from the relative adaptation of cardiac output influencing VO2max and also the recruitment of muscle mass" |
| Bijker KE, de Groot G, Hollander AP — 2002 | Differences in leg muscle activity during running and cycling in humans | Eur J Appl Physiol | Eccentric-concentric cycle in running vs. concentric-only in cycling as core mechanical difference |
| Friel J — n.d. | A Quick Guide to Setting Zones | [joefrieltraining.com](https://joefrieltraining.com/a-quick-guide-to-setting-zones/) | "Lactate Threshold Heart Rate is slightly different in running than it is in other aerobic activities" |
| Fitzgerald M, 80/20 Endurance — n.d. | Mastering Intensity Guidelines for 80/20 Triathlon | [8020endurance.com](https://www.8020endurance.com/intensity-guidelines-for-8020-triathlon/) | Sport-specific zones obligation as 80/20 methodology foundation |
| 220 Triathlon Magazine — n.d. | Best heart rate zones for running | [220triathlon.com](https://www.220triathlon.com/training/run-training/best-heart-rate-zones-for-running) | "Your cycling lactate threshold heart rate will be 5-10 bpm lower than your running lactate threshold heart rate because of the postural difference" |
| Runworks Coach Blog — 2014 | Running vs. Cycling Heart Rate | [runworks.com](http://www.runworks.com/2014/02/running-vs-cycling-heart-rate/) | 5-10 bpm run higher as consensus statement |

---

## Application in framework

### What is confirmed

- **CLAUDE.md "Sport-specific HR-zone application (MANDATORY)"** as a mandatory section is sport-scientifically well grounded. The ~8 bpm differential assumption in the athlete-specific `athlete_status.md` lies in the plausible middle range.
- **Watt targets as the primary control variable on the bike** (athlete_status.md "Primary for bike steering: watt + RPE") is methodologically correct — HR is a secondary anchor with higher inter-day variation and cross-sport variability.
- **Sport-specific time-trial tests** as a recommendation in `zone_validation_protocol.md` align with the Friel/80/20 consensus.

### What should be changed / refined

1. **`framework/CLAUDE.md` — "Sport-specific HR-zone application (MANDATORY)"** add a reference:
   - In the mechanism part, name this doc as the source
   - Clarification: the 5-10 bpm differential is the median; individually variable between 3-15 bpm
2. **`framework/config.example/training_paradigms.md`** — new section "Cross-sport HR differentials (typical)":
   - Table with typical differentials Run vs. Bike vs. Swim
   - Note: individual validation via a separate LTHR test per sport is mandatory
   - Reference this doc
3. **`framework/config.example/zone_validation_protocol.md`** — extension "One own test per sport":
   - Run LTHR test: 20-min running time trial
   - Bike LTHR test: 20-min indoor bike time trial with FTP anchor
   - Derive separate zone tables
4. **`framework/agents/specialist-endurance.md`** — mandatory section "Check bike-HR zones separately" (already exists implicitly via CLAUDE.md, but a direct reference hint in the agent prompt prevents drift)

### What stays unchanged

- **Watt > HR on the bike as the steering hierarchy** stays correct — HR is a sanity cap, not the primary control anchor.
- **Run-derived `context.hrZones`** in the output stays correct — that is the run-zone convention in the framework, the bike override is explicit via `athlete_status.md`.

---

## Open questions / Caveats

1. **Swim zones are currently irrelevant in the framework** (single-athlete focused on run + bike + ninja + strength). For a future triathlon extension, swim LTHR would be an additional sport anchor — the mechanism explanation in this doc remains applicable.

2. **HRmax drift with age** is not handled here — the typical drift is linear at ~1 bpm/year (Tanaka formula: 208 - 0.7 × age), but the relative differential run vs. bike stays constant over age. A dedicated doc section on HRmax drift would be conceivable, but is secondary.

3. **Treadmill vs. outdoor run HRmax:** treadmill run HRmax can be 2-5 bpm below outdoor run HRmax (lack of wind cooling, biomechanical differences). When applying the bike-vs-run differential it must be clear which run HRmax one compares against. Outdoor is the clean reference.

4. **Ergometer vs. outdoor bike HRmax:** indoor ergometer sessions typically show 3-5 bpm lower HRmax than outdoor climate sessions, due to worse thermoregulation + static position. That is athlete self-variation; the bike-vs-run differential stays the same.

5. **Triathlon brick effects:** on a brick run after the bike, the athlete typically shows a "shifted" HR response — higher HR per pace unit. This brick-specific adaptation is not covered here; see planned doc N3 (Brick-Running Intensity).
