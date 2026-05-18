# Concurrent training interference — strength + endurance in temporal sequence

**Created:** 2026-05-16

## TL;DR

1. **Concurrent training interference is real, but more moderate than often portrayed.** Wilson 2012 meta-analysis (21 studies, 422 effect sizes) shows: strength alone yields ES = 1.76 for 1RM gain; concurrent strength + endurance yields ES = 1.44 (loss ~18%). Hypertrophy loss even smaller (1.23 → 0.85). Power loss strongest (0.91 → 0.55 = ~40% loss).
2. **Mode matters:** "Resistance training concurrently with running, but not cycling, resulted in significant decrements in both hypertrophy and strength" (Wilson 2012). → Bike endurance is friendlier to strength build-up than run endurance.
3. **Molecular mechanism (Coffey & Hawley 2017):** AMPK ↔ mTOR antagonism. Aerobic training activates AMPK; AMPK inhibits mTORC1, which suppresses protein synthesis. But: "it seems unlikely that a few select proteins could mediate such events and explain the interference effect" — multifactorial.
4. **Practice recommendations** are less clear-cut than often communicated. Coffey & Hawley explicitly warn: "Recommendations to individuals to undertake divergent exercise modes on different days to avoid adaptation interference with concurrent training is oversimplistic." The ≥3h / ≥6h spacings established in the framework are conservative-sensible, but the exact hour values are **not directly mapped to hard study data**.

---

## Question / Trigger

In `config.example/training_paradigms.md` (lines 297-310) the framework anchors:
> "WeightTraining → run: ≥3h spacing. WeightTraining with leg focus (tags: legs / beine (legacy), plyo) → run: ≥6h spacing. Reason: leg strength before the run raises metabolic interference and CNS fatigue significantly. Sources: Coffey & Hawley (2017), Wilson et al. (2012)."

The sources are named, but the specific hour values (3h, 6h) are **not directly** supported in those sources. They are a pragmatic coach rule on the basis of the general interference evidence. Questions:

1. What does the literature say exactly about interference strength (which variable is reduced by how much)?
2. Which time spacings are actually study-empirically supported?
3. Does sequence (strength-first vs. endurance-first) play a role?
4. Does mode (run vs. bike) have an influence?

---

## Findings

### 1. Wilson 2012 meta-analysis — quantification of interference

**Wilson JM et al. 2012 (JSCR / MSSE):** Meta-analysis of 21 studies, 422 effect sizes.

| Endpoint | Strength only | Concurrent (strength + endurance) | Loss |
|----------|---------------|------------------------------------|------|
| Hypertrophy (muscle mass) | ES 1.23 | ES 0.85 | ~31% |
| 1RM strength | ES 1.76 | ES 1.44 | ~18% |
| Power (jump, speed) | ES 0.91 | ES 0.55 | ~40% |

**Key finding — mode specificity:**
> "Resistance training concurrently with running, but not cycling, resulted in significant decrements in both hypertrophy and strength."

→ Run endurance is **clearly** more interference-strong than bike endurance. Mechanics:
- Running has eccentric loading → higher muscle-damage profile → higher recovery competition with strength adaptation
- Cycling has almost only concentric → competes less for muscle-repair capacity

**Frequency and volume effects:**
- "Correlational analysis identified significant negative relationships between frequency and duration of endurance training for hypertrophy, strength, and power."
- Run volume > 30 min/day and frequency > 3-5×/week accumulate interference progressively

### 2. Molecular mechanisms — Coffey & Hawley 2017

Coffey & Hawley "Concurrent exercise training: do opposites distract?" (2017) is the methodologically cleanest molecular review:

**AMPK-mTOR axis:**
- Aerobic training → ATP use → AMP/ATP ratio rises → AMPK activated
- AMPK phosphorylates TSC2 and Raptor → inhibits mTORC1 complex
- mTORC1 is master regulator of protein synthesis (hypertrophy signal)
- → endurance shortly before strength or simultaneously: theoretically reduced hypertrophy

**But:** Coffey & Hawley are sceptical about the direct molecular explanation:
> "it seems unlikely that a few select proteins could mediate such events and explain the interference effect"

Multifactorial: AMPK, PGC-1α, glycogen stores, CNS fatigue, cortisol response, muscle damage. No single molecular explanation suffices.

**Practice recommendation by Coffey & Hawley:**
> "Recommendations to individuals to undertake divergent exercise modes on different days to avoid adaptation interference with concurrent training is oversimplistic and not representative of the 'real world' scenarios under which athletes train."

→ The simple "separate days" rule is not study-unambiguous. In practice a 6-h separation often works just as well as a 24-h separation.

### 3. Sequence effect — strength before endurance or vice versa?

**Coffey & Hawley:**
> "While we have observed some differences in the magnitude of effect in kinase phosphorylation … the overall responses in the 'metabolic' and 'myogenic' pathways were often similar, regardless of exercise mode, and any differences moderate."

**Doma & Deakin 2013** (see [eccentric-calf-pap-inhibition.md](eccentric-calf-pap-inhibition.md)) shows for acute performance:
> "running economy decreased within 8 hours after lower limb strength training"

→ **Within an 8-hour frame** strength-first-endurance-second (same day) is suboptimal for endurance quality. **Endurance-first-strength-second** is acutely less problematic — but then the whole training day is consumed for the heavy strength load.

**Pragmatic literature recommendation:**
- **If strength and endurance on the same day:** endurance first (Z2 run or similar), strength after with 4-6h rest
- **If strength on the previous day:** endurance session next day with at least 12-16h rest; with leg strength 24h rest
- **If endurance quality (Z4/Z5) on the same day:** strength at the earliest 4-6h afterwards, ideally on the previous day or next day

### 4. In framework: 3h/6h anchors

The framework rules "WeightTraining → run: ≥3h; leg focus → run: ≥6h" are a **pragmatic synthesis** that accounts for:

| Constellation | Framework rule | Study anchor |
|---------------|----------------|--------------|
| Easy run after upper-body strength | ≥3h | Doma 2013 (8h window for moderate effects; 3h is the lower bound) |
| Easy run after leg strength | ≥6h | Wilson 2012 (leg strength + run = highest interference) |
| Quality run (Z4/Z5) after leg strength | Recommendation: previous/next day | Doma 2013 + pragmatics |
| Strength after Z2 run | ≥3h possible | Coffey & Hawley: sequence minimally relevant |
| Strength after Z4/Z5 run | Recommendation: previous/next day | CNS fatigue + protein-damage recovery |

**Assessment:** the framework rules are defensively conservative. The 6h rule for leg strength + run is well grounded (Wilson 2012 mode effect + Doma 2013 8h window).

---

## Primary sources

| Author / year | Title | Publisher / link | Key quote |
|---------------|-------|------------------|-----------|
| Wilson JM, Marín PJ et al — 2012 | Concurrent Training: A Meta-Analysis Examining Interference of Aerobic and Resistance Exercises | [JSCR via Lippincott](https://journals.lww.com/nsca-jscr/fulltext/2012/08000/concurrent_training__a_meta_analysis_examining.35.aspx), [PubMed 22002517](https://pubmed.ncbi.nlm.nih.gov/22002517/) | "Resistance training concurrently with running, but not cycling, resulted in significant decrements in both hypertrophy and strength" |
| Coffey VG, Hawley JA — 2017 | Concurrent exercise training: do opposites distract? | [PMC 5407958](https://pmc.ncbi.nlm.nih.gov/articles/PMC5407958/) | "it seems unlikely that a few select proteins could mediate such events and explain the interference effect" |
| Coffey VG, Hawley JA — 2009 | Molecular responses to strength and endurance training: are they incompatible? | [PubMed 19448698](https://pubmed.ncbi.nlm.nih.gov/19448698/) | Foundation paper on the AMPK-mTOR antagonism hypothesis |
| Fyfe JJ, Bishop DJ, Stepto NK — 2014 | Interference between concurrent resistance and endurance exercise: molecular bases and the role of individual training variables | [PubMed 24728927](https://pubmed.ncbi.nlm.nih.gov/24728927/) | Practice variables (frequency, volume, mode, sequence) as moderators |
| Doma K, Deakin GB — 2013 | The effects of strength training and endurance training order on running economy and performance | (JSCR) | "running economy decreased within 8 hours after lower limb strength training" |
| Schumann M et al — 2022 | Compatibility of Concurrent Aerobic and Strength Training for Skeletal Muscle Size and Function: An Updated Systematic Review and Meta-Analysis | [PMC 8891239](https://pmc.ncbi.nlm.nih.gov/articles/PMC8891239/) | Update to Wilson 2012 data; confirms mode and volume effects |

---

## Application in framework

### What is confirmed

- **3h/6h anchors** are defensively conservative and consistent with Wilson 2012 + Doma 2013. The leg-strength → run-6h rule has the strongest study anchor (Wilson 2012 mode effect + Doma 2013 8h window).
- **Bike endurance is more interference-friendly than run endurance** → in practice, with bike sessions a 3h spacing to strength can be sufficient even with leg strength if the strength is upper-body focused.

### What should be changed / refined

1. **`framework/config.example/training_paradigms.md`** — refine the "Concurrent-training spacings" section:
   - Current 3h/6h anchors stay
   - Add: "Mode effect — bike endurance is more interference-friendly than run endurance (Wilson 2012). With strength + bike Z2, a 3h spacing is usually sufficient even with leg strength."
   - Sequence recommendation: on the same day prefer endurance first, then strength
   - Reference this doc and [eccentric-calf-pap-inhibition.md](eccentric-calf-pap-inhibition.md) (M11)
2. **`framework/agents/specialist-endurance.md`** — mandatory check on quality-session planning:
   - If leg strength in the last 24h: avoid quality run or reduced volume ceiling
   - If leg strength in today's plan AND quality run for today: force ordering (quality first, strength at earliest 6h later)
3. **`framework/scripts/validate_plan.py`** — consider a new rule:
   - If `legs` (or legacy `beine`) tag in strength workout < 6h before run workout with `intensity in {high, Z4, Z5}`: WARNING
   - Would be consistent with existing rules R001-R012

### What stays unchanged

- **The existence of the interference rule** remains — even if the simple "different days" rule is oversimplistic, the concrete 3h/6h operationalisation gives the coach clear decision anchors.

---

## Open questions / Caveats

1. **3h lower bound is a heuristic, not study-empirically supported.** Study data exist for 8h (Doma 2013) and 24h (Wilson 2012). The 3h is a pragmatic coach convention for "minimum gap to allow protein-synthesis-window separation".

2. **Masters-athlete-specific data are missing.** All cited studies are primarily trained adults 20-40 y. Masters may require longer spacings (24h+) between heavy strength + quality endurance sessions.

3. **Strength dose-response** is not unambiguous. Light strength (mobility, core, activation) has minimal interference; heavy strength (leg press, squats @ 80%+) has maximal interference. The 6h rule should differentiate — which in the framework currently only happens via the `legs` tag (legacy `beine` also accepted).

4. **Long run vs. quality:** long run (Z2, > 90 min) has more interference potential on strength adaptation than short quality sessions, due to cumulative mitochondrial-signal activation + glycogen depletion. A separate recommendation "long-run day: no strength on the same day" would be consistent — currently not hardcoded in the framework.

5. **Strava insights for endurance athletes** could flag concurrent violations — e.g. a brick-session run < 6h after leg strength could be marked as "compromised". That would be an extension of the `strava-publisher` logic.
