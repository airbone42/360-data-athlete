# Achilles tendinopathy rehab — phases, pain monitoring, return-to-sport criteria

**Created:** 2026-05-16

---

## TL;DR

1. **Sport-scientific standard is the 4-phase structure** per Silbernagel et al. (2020 Clinical Practice Guidelines):
   - **Phase 1 — symptom management & load reduction** (week 1-2+)
   - **Phase 2 — recovery** (week 2-5+)
   - **Phase 3 — rebuilding** (week 3-12+) — *here bilateral jumps + heavy load begin*
   - **Phase 4 — return-to-sport** (3-6 months+) — unilateral plyometrics, sport-specific load

2. **The pain-monitoring model per Silbernagel is the canonical steering heuristic:**
   - **VAS ≤ 5/10 during load** OK
   - **VAS ≤ 2/10 the next morning** mandatory
   - **No week-on-week escalation** of pain values
   - On violation of these criteria → step the phase back

3. **Plyometric clearance (phase 3 → 4 or rebuilding → return-to-sport):**
   - **VAS < 3/10 on two-leg heel raises with added load**
   - **Single-leg eccentric without flare-up for 2 weeks**
   - **VAS < 2/10 on 20 single-leg hops**
   - **6-8 weeks heavy-slow resistance with ≥30 lbs added load** before plyo introduction

4. **Our framework phases (1/2/3) are a simplified mapping of the Silbernagel 4 phases.** Our "phase 3 active, plyo cleared" functionally corresponds to the return-to-sport phase 4 with gradual plyo progression. **The explicit transition criteria between our phases were not previously documented** — should be docked to the Silbernagel criteria.

---

## Question / Trigger

In the framework Achilles phase tracking is used in two places:

1. **`athlete_static.md`** (athlete-specific) — e.g. "phase 3 active (plyo cleared)" as trigger for plyo sessions, hill sprints, hill running, surface choice
2. **`validate_plan.py` rule R005** — if plyo block + hard surface (asphalt/track) on the same day with Achilles phase 3 → WARNING

The transition criteria ("when may the athlete switch to phase 3?", "when must he return to phase 2?") are currently:
- In `athlete_static.md` mentioned as a phase-3 criterion, e.g. "morning stiffness gone, stair climbing/walking pain-free"
- But: what happens if morning stiffness returns? What if a plyo block ends painfully? Which pain threshold is "significant"?

Questions:

1. Which phase model is the sport-medical standard for mid-portion Achilles tendinopathy?
2. Which objective and subjective criteria define phase transitions?
3. Which pain-monitoring thresholds are evidence-based?
4. Which plyometric-clearance criteria are documented?

---

## Findings

### 1. Silbernagel 4-phase model — canonical standard

**Silbernagel KG et al (2020), JOSPT/ACSM Clinical Practice Guidelines "Current Clinical Concepts: Conservative Management of Achilles Tendinopathy":**

> "The rehabilitation of an athlete with Achilles tendinopathy can be divided into 4 phases: (1) symptom management and load reduction, (2) recovery, (3) rebuilding, and (4) return to sport."

**Phase 1 — symptom management & load reduction (week 1-2+):**
- Pain and difficulty with everyday load
- Pain on 10× single-leg heel raise
- Goal: first load, understand the pain-monitoring model, patient education
- Activity: minimal running, possibly running break, light isometric calf exercises

**Phase 2 — recovery (week 2-5+):**
- Phase 1 tolerated, no pain in the distal tendon section
- Eccentric loading (Alfredson 3×15 twice daily) starts
- Reintroduce running at VAS < 2 in daily life

**Phase 3 — rebuilding (week 3-12+):**
- "Heavier strength training, increase or begin running and/or jumping"
- Heavy-slow resistance (HSR) with progressive load (backpack/belt)
- **Bilateral plyometrics begins here** ("Plyometric training starts with bilateral jumps and progresses to unilateral jumps")
- Sport-specific load is introduced

**Phase 4 — return-to-sport (3-6 months+):**
- Full functionality restored
- Heel-rise test and jumping test functionally comparable to the unaffected leg
- "It is crucial to ensure that an athlete has full recovery of function, as measured with the heel-rise and jumping tests, along with symptomatic recovery."
- Unilateral plyometrics, hill sprints, full sport load

**Source:** Silbernagel KG, Hanlon S, Sprague A (2020). "Current Clinical Concepts: Conservative Management of Achilles Tendinopathy." → [PMC 7249277](https://pmc.ncbi.nlm.nih.gov/articles/PMC7249277/) (Plus PubMed 32267723)

### 2. Pain-monitoring model — steering heuristic per Silbernagel

**Silbernagel et al. (2007, randomized controlled study):** pain monitoring during rehab significantly improves outcome values over rigid pause.

**Thresholds per activity level (2020 guidelines):**

| Activity level | Pain during | Pain after (next morning) | Recovery days |
|----------------|-------------|---------------------------|---------------|
| Light | 1-2/10 | 1-2/10 | 0 (daily OK) |
| Medium | 2-3/10 | 3-4/10 | 2 days |
| High | 4-5/10 | 5-6/10 | 3 days |

**Important additional rule:** "Pain after exercises was allowed to reach 5 on the VAS but should have subsided by the following morning, and pain and stiffness in the Achilles tendon were not allowed to increase from week to week."

→ Phase escalation may NOT take place if VAS values stay rising over more than 1 week. Phase step-back is mandatory.

**Source:** Silbernagel KG et al (2007). "Continued sports activity, using a pain-monitoring model, during rehabilitation in patients with Achilles tendinopathy: a randomized controlled study." Am J Sports Med. → [PubMed 17307888](https://pubmed.ncbi.nlm.nih.gov/17307888/)

### 3. Return-to-plyometric criteria (phase 3 → 4)

From the 2020 guidelines and more concrete practice protocols (Physiopedia, JOSPT 2015):

- **Walking pain-free or VAS ≤ 1-2/10**
- **6-8 weeks heavy-slow resistance** with progressive load (≥30 lbs added)
- **Bilateral calf raises** with added weight at VAS < 3/10
- **Single-leg eccentric** without flare-up over 2 weeks
- **20 single-leg hops** with VAS < 2/10

→ Bilateral plyometrics (box jumps, two-leg drop jumps) begins here.
→ **Unilateral plyometrics** (single-leg hops, drop jumps, hill sprints) is only introduced after 2-4 weeks of successful bilateral plyo.

### 4. VISA-A as objective outcome marker

**VISA-A** (Victorian Institute of Sport Assessment - Achilles): questionnaire, score 0-100, asymptomatic = 100. Recommended for serial follow-up (weekly measurement interval) as a phase-transition anchor.

> "The VISA-A is based on an inverted numeric rating scale and results in a score range from 0 to 100 points with asymptomatic persons expected to score 100 points." (Robinson 2001, validation study) → [PMC 3273883](https://pmc.ncbi.nlm.nih.gov/articles/PMC3273883/)

Phase-transition recommendation in the literature:
- VISA-A ≥ 50 → phase 2 → 3 (rebuilding)
- VISA-A ≥ 80 → phase 3 → 4 (return-to-sport)
- VISA-A ≥ 90 with stable function over 2-4 weeks → full sport clearance

### 5. Alfredson eccentric protocol — core element of phases 2-3

**Alfredson H, Pietilä T, Jonsson P, Lorentzon R (1998):** 3×15 eccentric heel drops, twice daily, 7 days/week, 12 weeks. 180 reps/day. With pain-freeness: backpack loading progressively.

**Stevens & Tan (2014) JOSPT:** lower-volume variant (do-as-tolerated) is equivalent in outcome — the athlete need not adhere to the rigid 180-rep prescription, as long as "pain to tolerance" is the steering principle.

**Source:** Effectiveness of the Alfredson protocol compared with a lower repetition-volume protocol for midportion Achilles tendinopathy → [PubMed 24261927](https://pubmed.ncbi.nlm.nih.gov/24261927/)

**Heavy-slow resistance (HSR) vs. pure eccentric:** both effective; HSR showed higher patient satisfaction after 12 weeks. Both approaches belong in our phase 2-3 toolkit.

---

## Primary sources

| Author / year | Title | Publisher / link | Key quote |
|---------------|-------|------------------|-----------|
| Silbernagel KG, Hanlon S, Sprague A — 2020 | Current Clinical Concepts: Conservative Management of Achilles Tendinopathy | [PMC 7249277](https://pmc.ncbi.nlm.nih.gov/articles/PMC7249277/) | "The rehabilitation of an athlete with Achilles tendinopathy can be divided into 4 phases: (1) symptom management and load reduction, (2) recovery, (3) rebuilding, and (4) return to sport." |
| Silbernagel KG et al — 2007 | Continued sports activity, using a pain-monitoring model, during rehabilitation in patients with Achilles tendinopathy: a randomized controlled study | [PubMed 17307888](https://pubmed.ncbi.nlm.nih.gov/17307888/) | "Pain after exercises was allowed to reach 5 on the VAS but should have subsided by the following morning, and pain and stiffness in the Achilles tendon were not allowed to increase from week to week." |
| Alfredson H, Pietilä T, Jonsson P, Lorentzon R — 1998 | Heavy-load eccentric calf muscle training for the treatment of chronic Achilles tendinosis | Am J Sports Med | 3×15 eccentric, 2×/day, 12 weeks = 180 reps/day |
| Stevens M, Tan CW — 2014 | Effectiveness of the Alfredson protocol compared with a lower repetition-volume protocol for midportion Achilles tendinopathy: a randomized controlled trial | [PubMed 24261927](https://pubmed.ncbi.nlm.nih.gov/24261927/) | Do-as-tolerated equivalent to fixed 180-rep prescription |
| Robinson JM et al — 2001 | The VISA-A questionnaire: a valid and reliable index of the clinical severity of Achilles tendinopathy | [PMC 3273883](https://pmc.ncbi.nlm.nih.gov/articles/PMC3273883/) | VISA-A 0-100, asymptomatic = 100, test-retest reliability for progress monitoring |
| Silbernagel KG, Crossley KM — 2015 | A Proposed Return-to-Sport Program for Patients With Midportion Achilles Tendinopathy | JOSPT 45(11), 876-886 (paywalled, [doi.org/10.2519/jospt.2015.5885](https://www.jospt.org/doi/abs/10.2519/jospt.2015.5885)) | Detailed phase programming for return-to-sport |
| Physiopedia | Achilles Tendinopathy Toolkit: Section D — Exercise Programs | [physio-pedia.com](https://www.physio-pedia.com/Achilles_Tendinopathy_Toolkit:_Section_D_-_Exercise_Programs) | Phase 1/2 definitions, clinical practice derivations |

---

## Application in framework

### What is confirmed

- **Phase-based tracking is evidence-based** — the 4-phase Silbernagel structure is clinical standard.
- **Pain monitoring instead of strict pause** is evidence-superior (Silbernagel 2007).
- **Plyo block in early phases + gradual reintroduction** in phase 3+ is clinically correct.
- **R005 validator rule** "Plyo + hard surface with Achilles phase 3 → WARNING" is conservative-sensible, because hard surface in early phase 3 can still lead to eccentric load spikes.

### What should be changed / refined

1. **`framework/config.example/athlete_static.md`** — map phase definition as a template to the Silbernagel 4-phase model:
   - Recommendation: phase numerics simplified 1/2/3 = (Silbernagel 1+2 / Silbernagel 3 / Silbernagel 4) — explicitly documented
   - Per phase: transition criteria (VAS thresholds, function tests, minimum weeks) as template block
2. **`framework/agents/physio-consultant.md`** and **`framework/agents/sports-ortho-consultant.md`** — mandatory section "Achilles phase transition":
   - On athlete-phase-switch request: check pain-monitoring thresholds (VAS values from NOTEs/athlete feedback)
   - Query plyo-clearance checklist (6-8 weeks HSR, single-leg hop test, VAS thresholds)
   - Reference this doc
3. **`framework/scripts/validate_plan.py` R005** — extend the header comment:
   - Reference this doc as sport-science anchor for the WARNING logic
   - Clarification: WARNING (not ERROR), because gradual plyo introduction on hard surface in stable phase 3 can be tolerated
4. **`framework/config.example/athlete_static.md`** — introduce an optional VISA-A score block:
   - Athletes can enter the VISA-A score weekly
   - Objective progress metric for phase-transition discussions

### What is not changed

- **Our 3-phase simplification** remains as a practical model — the mapping to Silbernagel 4 is documented transparently, but no switch to 4-phase numerics required (would invalidate all athlete configurations).
- **R005 as WARNING (not ERROR)** stays correct — the plyo block on hard surface is a precaution recommendation, not a hard no-go in phase 3.

---

## Open questions / Caveats

1. **Athlete-specific phase data stay in `athlete_status.md`/`athlete_static.md`** — this doc provides only the generic logic. Concrete phase-3 start dates, VAS-trend NOTEs etc. belong in the wrapper.

2. **Insertional vs. mid-portion Achilles tendinopathy:** this doc focuses on mid-portion (most common case, Silbernagel studies are primarily on it). Insertional (at the calcaneal insertion) has different eccentric-loading recommendations (reduction of dorsiflexion depth). If athlete has the insertional form, separate research needed.

3. **Re-injury risk is high in the return-to-sport phase** — "there is a high propensity for recurrence, especially during the return-to-sport phase." The validator WARNING on plyo + hard surface therefore remains permanently sensible, even if the phase is formally active-3.

4. **Heel-rise test and jumping test as objective phase-transition markers** should be integrated into the audit workflow — who tests them? When? Currently the phase classification is coach/athlete consensus-based, not function-tested.

5. **Bridge to HSR/eccentric protocols:** concrete heel-raise progressions (Alfredson 3×15, HSR with load) are currently maintained in `exercise_progressions.md` as individual exercise entries. A generic variant for other athletes would live in a separate research doc "Achilles rehab exercise protocols".
