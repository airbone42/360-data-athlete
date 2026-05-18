# VO2max short intervals (30/15 Rønnestad, 30/30 Billat) — intensity, volume, scaling

**Trigger:** Rønnestad incident from real application — compliance below 90% and decoupling above 10% in a 2×13×30/15 set; subsequent naive re-prescription of the same protocol despite the drop evidence.

---

## TL;DR

1. **Intensity for the 30/15 format:** classically `100% MAP` (Maximum Aerobic Power = power that just triggers VO2max, ~5-min peak). In trained cyclists this typically corresponds to **105-120% FTP**, **not 130-145% FTP**. (Caveat: this figure corresponds to 5-min-peak power = 5MMP. Rønnestad's strict original definition refers to the 1-min ramp-peak power, which lies at ~130-140% FTP — see [map-ftp-ramp-test.md](map-ftp-ramp-test.md). Coach literature uses 'MAP' inconsistently for both values; in what follows we mean the practically usable 5MMP variant.) The "30s = 130-145% FTP" rule previously held in `config/training_paradigms.md` was a **confusion with anaerobic-capacity zones** and is overridden by this document.

2. **Volume for re-build after a compliance incident:** a set should **not be repeated 1:1** after a session with compliance < 95%. Coach Ben entry recommendation 2–3 sets × 9 reps; with a demonstrated volume limit (e.g. 19/26 = ~73% of the target volume completed) → **3×8 @ MAP range** is the clean re-entry stage.

3. **Set configuration:** at equal total volume, **more, shorter sets** are more robust than few, longer ones — the additional 3-min set rests give a cardiac reset and increase completion probability. **3×8 > 2×10 ≈ 2×12** at the same total-reps budget.

---

## Question / Trigger

**Trigger incident:** from real application — an athlete completed a Rønnestad 2×13×30/15 session at a watt target corresponding to a ~130% FTP prescription. Activity data: compliance clearly below 90%, decoupling clearly above 10%, set 2 aborted before set end. The watt target was reached in the average output, but the volume was not sustainable.

**Follow-up incident:** in the subsequent /training workflow the same 2×13×30/15 protocol was naively re-proposed — because `fetch_type_history --type Ride` did not return the VirtualRide session (type-filter bug) and the planner does not check compliance history.

**Concrete questions to sport science:**
1. Which intensity is prescribed in the original Rønnestad 30/15 protocol?
2. Which set/rep configurations are evidence-based for athletes below elite (trained, but not WorldTour)?
3. What does the literature say about scaling after an abort — volume down, intensity down, or both?
4. When is more-sets-shorter-sets (3×8) better than fewer-sets-longer-sets (2×12) at the same total volume?

---

## Findings

### 1. Intensity prescription in the Rønnestad protocol

**Original protocol (Rønnestad et al, 2015 / 2020):** "MAP as exercise intensity, where MAP = minimal power output eliciting peak VO2" + "recovery period being 50% of the work duration at intensity equal to 50% of MAP". Work:recovery ratio = 2:1 (30s on / 15s off), 3 × 13 reps in the elite version, 3 min rest between sets.

**MAP definition in practice:** MAP is the lowest power at which VO2max is reached — usually measured via a stepped test ("ramp test") as the 1-min or 5-min peak power. In trained cyclists MAP is typically **105-120% FTP**:
- Cyclists with a strong aerobic system (diesel type): MAP closer to 110-115% FTP
- Cyclists with a higher anaerobic share (sprinter): MAP closer to 115-120% FTP
- Rule of thumb: MAP ≈ FTP × 1.10-1.20, individually variable — best validated via the actual 5-min MMP value

**Definitional clarification (see [map-ftp-ramp-test.md](map-ftp-ramp-test.md)):** the 105-120% FTP cited here corresponds to the **5-min peak power (5MMP)**, often used in coach practice as a "MAP proxy". Rønnestad's academically strict MAP definition (1-min ramp peak in a stepped test) typically lies at **130-140% FTP**. Both values are cited in the literature as "MAP" — which is inconsistent. For our practical 30/15 prescription we use the lower band (5MMP variant, 105-120% FTP), because it is more conservative and remains sustainable for most trained cyclists. Athlete-specific validation via actually-completed prior sessions remains mandatory.

**Source:** Rønnestad BR, Hansen J (2013). "Optimizing interval training at power output associated with peak oxygen uptake in well-trained cyclists." Final findings: "fixed 30-second work intervals can be used to optimize training time at MAP and time ≥90% of VO2peak in well-trained cyclists using MAP exercise intensity and a 2:1 work:recovery ratio." → [PubMed 23942167](https://pubmed.ncbi.nlm.nih.gov/23942167/)

### 2. The 130-145% FTP trap: "intensified short intervals"

**Frontiers 2024 (Skovgaard et al, n=12 trained middle-distance runners):** Compared 4×3 min @ 95% vVO2max (long, "classic") vs. 24×30s @ 100% vVO2max + 30s @ 55% (short, "intensified"). Finding: **"The time spent above 90% VO2max was significantly lower in the 30-s intervals…compared to the 3-min session (201.3 ± 268.4 s vs. 327.9 ± 146.8 s, p = 0.05)."**

Concretely: 3.4 min vs. 5.5 min time above 90% VO2max. The higher recovery share (55% vs. 50% vVO2max) AND the higher work intensity (100% vs. 95% vVO2max) prevented VO2 from dropping enough between reps to stay high across the sets: **"the interval and recovery VO2 for the short interval runs are almost identical at approximately 78% VO2max, blocking the stimulus needed for sustained VO2max accumulation."**

**Implication for 30/15:** anyone who sets the watt target in 30/15 reps ABOVE MAP (= "intensified") gets **less** time-above-90% VO2max out of it, not more. Our previous "130-145% FTP" rule structurally shifted the reps into the range where the athlete burns anaerobic reserves, VO2 cannot stabilise, and the stimulus is smaller than at MAP intensity.

**Source:** "Faster intervals, faster recoveries — intensified short VO2max running intervals are inferior to traditional long intervals in terms of time spent above 90% VO2max" (Frontiers in Sports and Active Living, 2024) → [Frontiers DOI](https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2024.1507957/full)

### 3. Volume scaling — entry and re-build

**Coach Ben Delaney (Road Cycling Academy, TrainingPeaks 2023):** recommends as entry to the 30/15 format **"two to three sets of nine reps each"** at a target intensity of **"around 110% of threshold during the 30 seconds 'on' and 50% during the 15 seconds 'off'"**. Progression follows "gradually increase reps or intensity over time" — one axis per step, not both at once.

**Re-build logic after a compliance incident (own derivation from the three sources):**
- Compliance < 95% in the last session of the same format class → no 1:1 repeat
- Two axes for reduction: volume (total reps) OR intensity (watt anchor)
- With demonstrable intensity overshoot (decoupling > 10%, set 2 not held) → **both** axes reduced slightly is more robust than one drastically
- Coach Ben entry 2-3×9 is the lower bound of the sensible build-up — sensible anchor for re-build after a drop

**Source:** Coach Ben, Road Cycling Academy via TrainingPeaks → [trainingpeaks.com/blog/ronnestad-30-15-intervals](https://www.trainingpeaks.com/blog/ronnestad-30-15-intervals/)

### 4. More-sets-vs-longer-sets at equal total volume

**Indirectly from Spare Cycles (2019) data — VO2 kinetics at 30/15:** "HR rise is slower and can be disrupted by the first micro-rest, causing HR to initially plateau lower than 90%. HR is subsequently more stable than VO2, meaning once it's above 90% HRmax it usually remains above that level." In an example session in the blog post HR fell by about 25 bpm on a skipped rep within a few seconds — very rapid drop.

**Implication:** within a set, VO2 builds up, but in longer sets it drops at the end of the set when breathing/HR overload. **Shorter sets with more rest-sets:**
- Reduce the probability of a drift-induced drop at set end
- Give a 3-min cardiac reset between sets — set 2 starts cleaner
- Accumulated time-above-90% VO2max is in total higher, because fewer reps are "lost" below the stimulus

At the same total reps (e.g. 24): **3×8 > 2×12 > 1×24** when compliance is fragile.

**Source:** Spare Cycles 2019, "Comparing 30/15 VO2max Intervals" → [sparecycles.blog](https://sparecycles.blog/2019/03/13/comparing-30-15-vo2max-intervals/)

### 5. Empirical data points from the research

- Rønnestad & Hansen 2015: 3×13×30/15 vs. 4×5min, 10 weeks, well-trained cyclists → **+5% FTP gain** for 30/15 group
- Rønnestad 2020 (elite, VO2max 68-77 ml/min/kg): 3×13×30/15 as standard protocol at WorldTour level
- Billat 1999: 30/30 @ vVO2max accumulates **7:51 min** time @ VO2max vs. **2:42 min** with continuous load — time-at-target is the decisive stimulus

---

## Primary sources

| Author / year | Title | Publisher / link | Key quote |
|---------------|-------|------------------|-----------|
| Rønnestad BR, Hansen J — 2013 | Optimizing Interval Training at Power Output Associated With Peak Oxygen Uptake in Well-Trained Cyclists | [PubMed 23942167](https://pubmed.ncbi.nlm.nih.gov/23942167/) | "fixed 30-second work intervals can be used to optimize training time at MAP and time ≥90% of VO2peak in well-trained cyclists using MAP exercise intensity and a 2:1 work:recovery ratio" |
| Rønnestad BR, Hansen J et al — 2015 | Effects of 12 weeks of block periodization on performance and performance indices in well-trained cyclists | [PubMed via Wiley](https://onlinelibrary.wiley.com/doi/abs/10.1111/sms.12309) | Comparison 3×13×30/15 vs. 4×5min Z5 — +5% FTP over 10 weeks |
| Rønnestad BR et al — 2020 | Superior performance improvements in elite cyclists following short-interval vs effort-matched long-interval training | [PubMed 31977120](https://pubmed.ncbi.nlm.nih.gov/31977120/) | Elite cyclists VO2max 68-77 ml/min/kg, 3×13×30/15 as standard |
| Skovgaard C et al — 2024 | Faster intervals, faster recoveries — intensified short VO2max running intervals are inferior to traditional long intervals in terms of time spent above 90% VO2max | [Frontiers in Sports and Active Living](https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2024.1507957/full) | "intensified short format performed worse… 201.3 s vs 327.9 s above 90% VO2max, p=0.05" |
| Billat V — 1999 | Interval training for performance: A scientific and empirical practice | [Sports Med PubMed](https://pubmed.ncbi.nlm.nih.gov/11227980/) | 30/30 @ vVO2max → 7:51 min @ VO2max |
| Coach Ben Delaney (Road Cycling Academy) — 2023 | Rønnestad 30/15 Intervals: An Inside Look | [TrainingPeaks Blog](https://www.trainingpeaks.com/blog/ronnestad-30-15-intervals/) | "Begin with two to three sets of nine reps each at 110% of threshold" |
| Spare Cycles (Anonymous Coach Blog) — 2019 | Comparing 30/15 VO2max Intervals | [sparecycles.blog](https://sparecycles.blog/2019/03/13/comparing-30-15-vo2max-intervals/) | HR-drift and VO2-kinetics analysis with practice data |
| Spare Cycles — 2017 | Prescribing VO2max | [sparecycles.blog](https://sparecycles.blog/2017/12/13/prescribing-vo2max/) | "no easy way to prescribe this workout based on percentage of FTP, since everyone will have a different relationship between MAP and FTP" |

---

## Application in framework

### What changes

1. **`config/training_paradigms.md` + `framework/config.example/training_paradigms.md`** — power-zone table for 30s reps:
   - **Old:** "30s power: 130–145% FTP (anaerobic capacity)"
   - **New:** "30s power in the 30/15 format: ~100% MAP, individually 105–120% FTP. Validate the watt anchor via actually-completed prior sessions, NOT via an FTP multiplier alone." Reference this document as the source.

2. **`framework/agents/specialist-endurance.md`** — new mandatory section "Compliance check before structured quality format":
   - Before any repetition of a known interval format (Rønnestad 30/15, Billat 30/30, threshold reps, VO2max long sets) read `interval_summary`, `compliance`, `decoupling` of the last activity of the same format
   - Compliance < 95% OR decoupling > 10% → volume AND/OR intensity must be reduced before the next attempt (see section 3 above)
   - Justification obligation in `coaching_notes`: "last session of the same format class compliance <90% / decoupling >10% → volume reduced (e.g. 3×8 instead of 2×13), watt anchor corrected into the MAP range (105-120% FTP)"

3. **`framework/scripts/fetch_type_history.py`** — type alias map:
   - `Ride → {Ride, VirtualRide}`
   - `Run → {Run, VirtualRun, TrailRun}`
   - Indoor sessions must no longer fall under the table

4. **`framework/CLAUDE.md`** — new mandatory section "Research-before-scaling-or-new-protocol":
   - Before scaling a stimulus (up or down) OR introducing a new exercise / new format: consult `framework/research/`
   - If no research entry exists: research first + persist it, then adapt
   - Not "because study X" without a source entry — all study references must be findable here

### What stays unchanged

- If `athlete_status.md` carries a historically validated sprint-power value for 30 s, it stays unchanged — that is the **all-out 30s peak** of the respective athlete, not the Rønnestad target. Clarify in the entry: this value is NOT the 30/15 prescription.
- Rules of thumb for volume scaling via CTL (CTL 20-30 → reduced volume ceiling) remain valid — only the concrete set/rep proposals are refined.

---

## Open questions / Caveats

1. **Individual MAP of the respective athlete:** without a direct MAP measurement, `FTP × 1.10–1.20` remains an estimate with individual scatter. Clean measurement via a ramp test (e.g. INSCYD protocol or classical stepped protocol +20W/min from moderate starting load to exhaustion); afterwards update the watt anchor in the athlete-specific status file.

2. **Endurance specialist as a research bridge:** the "compliance check" rule derived here only works when `interval_summary` is reliably filled. In some FIT files / Wahoo sessions the value is patchy. Fallback heuristics should be added (e.g. "total reps completed via lap count").

3. **Source-selection bias:** the studies referenced here are all from the "well-trained / elite cyclists" (Rønnestad) or "trained middle-distance runners" (Frontiers 2024) area. For **masters athletes 40+** with a mixed sport background (triathlon, ninja, run) there are no specific 30/15 studies. Application remains deductive from the trained-cyclist literature.

4. **Frontiers 2024 is a running study:** the main evidence for "intensified short intervals are worse" comes from a running study. Transfer to the bike is plausible (same physiological logic: VO2 stabilisation across reps), but strictly speaking extrapolated. A bike-specific validation of the statement is still pending.
