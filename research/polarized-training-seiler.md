# Polarized training-intensity distribution — Seiler 80/20 as evidence-based standard

**Created:** 2026-05-16

---

## TL;DR

1. **Polarized distribution = ~80% Z1-low + ~20% Z4/Z5-high, with Z2/Z3-threshold marginal (≤5%).** Empirically documented in elite endurance athletes across sport disciplines (rowing, cycling, cross-country skiing, running). Stöggl & Sperlich 2014 showed in a 9-week intervention with trained athletes **VO2peak gain +11.7% (POL) vs. +4.8% (HIIT) vs. ~0% (THR/HVT)**.

2. **Pyramidal distribution** (Z1 dominant, Z2/Z3 decreasing with height) is the historical practice variant, dominant in many WorldTour cyclists. **Treff 2019, Casado 2022:** show that pyramidal can be advantageous in the early season, polarized in the race-specific phase.

3. **Z3 is not "forbidden" — but reduced.** The polarized logic is NOT "never any Z2/Z3", but "Z2/Z3 is not the *primary* training zone". Easy tempo swings into Z2/Z3 are allowed, but permanently positioned threshold training generates more fatigue than VO2 stimulus.

4. **For a masters athlete with a multi-sport background:** polarized as the default is evidence-based sensible. The season-phase variation (pyramidal in off-season build, polarized in race-specific) is legitimate and can be athlete-specifically periodised via `competition_plan.md`.

---

## Question / Trigger

`config.example/training_paradigms.md` postulates in lines 22-34:

> "80% of sessions in Z1–Z2 (easy), 20% in Z4–Z5 (hard). Z3 is actively avoided."

Sources Seiler 2010, Stöggl & Sperlich 2014/2015 are named in the bibliography section, but:
- Original texts with full-text quotes are not stored
- The "active avoidance of Z3" is a strong statement — what does the literature really say?
- Transferability to masters athletes + multi-sport constellation not explicitly documented

Questions:
1. What is the original definition of polarized training per Seiler?
2. What does the empirical distribution in elite athletes look like exactly?
3. What does the comparison study Stöggl & Sperlich 2014 say?
4. When is pyramidal vs. polarized preferable?

---

## Findings

### 1. Original definition: Seiler 2010

Stephen Seiler (University of Agder) coined the polarized model from the retrospective analysis of training logs of elite endurance athletes:

- **~80% of training volume below LT1** (= "first lactate threshold", ~2 mmol/L blood lactate) → zones 1-2 in Coggan notation, Z1 in Seiler's 3-zone model
- **~20% of volume above LT2** (= "second lactate threshold", ~4 mmol/L) → zones 4-5 in Coggan, Z3 in Seiler's 3 zones
- **Z2 threshold (between LT1 and LT2)** = only ~5% or less

> Seiler & Kjerland 2006: "a polarized training intensity distribution with a greater proportion of zone 1 (75–78%) and zone 3 (15–20%) compared to zone 2 (4–10%)."

### 2. Empirical distribution in elite (Stöggl & Sperlich 2015 review)

Across endurance sports (Frontiers Physiology 2015):

| Sport | Z1 (low) | Z2 (threshold) | Z3 (high) |
|-------|----------|----------------|-----------|
| Elite rowing | 77-90% | 6-17% | 6-10% |
| Pro cycling | 70-88% | 11-22% | 2-8% |
| Cross-country skiing | 84-91% | (variable) | (variable) |
| Running | 77-86% | 5-12% | 8-15% |

**Important distinction in the original:** "elite endurance athletes perform approximately 80% of their training at low intensity (< 2 mM blood lactate) with about 20% high-intensity work" — but **the distribution within the high 20% varies.** Pure polarized = almost everything in Z3 (Z2-threshold marginal); pyramidal = decreasing distribution Z2 > Z3.

→ "experimental studies lasting 6 weeks to 5 months demonstrate superior responses to polarized TID, especially when compared with TID that emphasizes THR or HVLIT."

→ Caveat: "an 'optimal' TID cannot be identified" universally — individual adaptation to sport, athlete, season phase is mandatory.

### 3. Direct comparison: Stöggl & Sperlich 2014 RCT (n=48)

**Study:** 48 well-trained endurance athletes (runners, cyclists, triathletes, cross-country skiers), 9 weeks, four intervention arms:

| Arm | TID distribution | Description |
|-----|------------------|-------------|
| HVT (high-volume) | 83/16/1% (Z1/Z2/Z3) | Pyramidal-volume-focused |
| THR (threshold) | 46/54/0% | Threshold-only |
| HIT (high-intensity) | 43/0/57% | Fast-only HIIT, no Z2 |
| POL (polarized) | 68/6/26% | Classic polarized |

**Outcomes after 9 weeks:**

| Variable | HVT | THR | HIT | POL |
|----------|-----|-----|-----|-----|
| VO2peak Δ% | ~0 | ~0 | +4.8% | **+11.7%** |
| TT performance Δ% | minimal | minimal | +8.8% | **+17.4%** |

> "POL resulted in the greatest improvements in most key variables of endurance performance in well-trained endurance athletes. THR or HVT did not lead to further improvements in performance related variables."

**Source:** Stöggl T, Sperlich B (2014). "Polarized training has greater impact on key endurance variables than threshold, high intensity, or high volume training." Frontiers in Physiology. → [PMC 3912323](https://pmc.ncbi.nlm.nih.gov/articles/PMC3912323/)

### 4. Pyramidal vs. polarized — season periodisation

Casado et al. 2022 and newer meta-analyses suggest:

- **Off-season build:** pyramidal-leaning distribution (more Z2 threshold volume) builds threshold power solidly
- **Race-specific phase (8-12 weeks before race):** switch to polarized — more Z3 VO2max stimulus, Z2 threshold reduced
- **Taper phase:** reduction in both endpoints, race-pace practice in the foreground

→ Consistent with the existing framework logic (`training_paradigms.md` CTL threshold switch between polarized/pyramidal).

### 5. Z3 avoidance — actually or with nuance?

The hardcoded statement "Z3 is actively avoided" in `training_paradigms.md` is a simplification. A more precise reading:

- **Permanently positioned threshold training** (THR arm in Stöggl & Sperlich): brings nothing for VO2max, accumulates fatigue
- **Occasional Z2/Z3 tempo sessions** as race-specific preparation: are not "forbidden", but deliberately dosed
- **Z3 as a mix into Z1-Z2 sessions** (e.g. easy run that drifts due to wind or profile): unproblematic

→ Clarification in `training_paradigms.md`: "Z3 threshold is not the primary stimulus zone; targeted threshold sessions are allowed but not more often than 1×/2 weeks as race preparation."

---

## Primary sources

| Author / year | Title | Publisher / link | Key quote |
|---------------|-------|------------------|-----------|
| Seiler S, Kjerland GØ — 2006 | Quantifying training intensity distribution in elite endurance athletes: is there evidence for an "optimal" distribution? | Scand J Med Sci Sports | "polarized training intensity distribution with a greater proportion of zone 1 (75-78%) and zone 3 (15-20%) compared to zone 2 (4-10%)" |
| Seiler S — 2010 | What is best practice for training intensity and duration distribution in endurance athletes? | Int J Sports Physiol Perform | Foundational paper of the polarized concept |
| Stöggl T, Sperlich B — 2014 | Polarized training has greater impact on key endurance variables than threshold, high intensity, or high volume training | [PMC 3912323](https://pmc.ncbi.nlm.nih.gov/articles/PMC3912323/) | "POL resulted in the greatest improvements in most key variables of endurance performance in well-trained endurance athletes" |
| Stöggl T, Sperlich B — 2015 | The training intensity distribution among well-trained and elite endurance athletes | [PMC 4621419](https://pmc.ncbi.nlm.nih.gov/articles/PMC4621419/) | "elite endurance athletes perform approximately 80% of their training at low intensity (< 2 mM blood lactate) with about 20% high-intensity work" |
| Casado A et al — 2022 | Periodization and Optimal Training Intensity Distribution Models in World-class Long-distance Runners | (Review of world-class long-distance runners) | Pyramidal in early season, polarized in pre-race specific phase |
| Treff G et al — 2019 | The Polarization-Index: A Simple Calculation to Distinguish Polarized From Non-polarized Training Intensity Distributions | Frontiers Physiology | Polarization-Index as objective measure for TID classification |

---

## Application in framework

### What is confirmed

- **80/20 polarisation as framework default** is evidence-based for "well-trained endurance athletes" (Stöggl & Sperlich 2014 population matches our athlete profile).
- **CTL threshold switch between polarized and pyramidal** in `training_paradigms.md` is sport-scientifically consistent.
- **Stöggl & Sperlich 2014 as the RCT anchor** is the clean source for VO2peak comparison values.

### What should be changed / refined

1. **`framework/config.example/training_paradigms.md`** — clarification of the Z3 logic:
   - Replace the old statement "Z3 is actively avoided" with a more nuanced statement: "Z3 threshold is not the primary stimulus zone of the polarized distribution. Targeted threshold sessions are not forbidden, but not more often than 1×/2 weeks as race-specific preparation."
   - Reference this doc + cross-reference to pyramidal-distribution.md (planned M2)
2. **`framework/agents/specialist-endurance.md`** — on Z3 session proposals:
   - Check: does this fit the polarisation distribution of the last 7-14 days?
   - If Z3 > 10% of volume in the last 14 days: signal that there is a skew risk
3. **Periodisation switch in athlete setup:**
   - The `competition_plan.md` "Phase periodisation" section could explicitly carry pyramidal (build) vs. polarized (race-specific) as a phase marker

### What stays unchanged

- The **2-hard-stimuli-per-week strategy** as a practical operationalisation of the 20% high intensity remains correct — with 5-6 sessions/week, 2 quality sessions correspond exactly to the 20% mark.

---

## Open questions / Caveats

1. **Masters-athlete-specific data are missing.** All cited studies are primarily in trained athletes 22-35 years old. The transfer to masters 40+ (slower recovery, higher injury susceptibility on Z3) is deductively plausible but not study-verified.

2. **Multi-sport-athlete-specific data:** studies are sport-specific (runners, cyclists, triathletes separately). For multi-sport constellations (run + bike + ninja) a direct evidence anchor would be helpful — but it doesn't exist in this study form.

3. **Stoeggl & Sperlich 2014 in TID classification:** the POL group actually had only 26% Z3 (not 20%) — a slightly "hotter" polarized variant than the classic Seiler model. That is methodologically a small inconsistency, but does not change the core statement.

4. **Polarization-Index as objective classification:** Treff 2019 propose a quantitative index — would be a sensible extension for our `zoneDistribution` output in `fetch_context.py`. Action item: evaluate after phase 4.
