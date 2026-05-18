# Strides — neuromuscular priming, running economy, format parametrisation

**Trigger:** in the framework, strides are mentioned in several places (`config.example/training_paradigms.md` §264, §273, §319-323, §452; `agents/specialist-endurance.md` strides section; `agents/strava-publisher.md`; `agents/data-scientist.md`) — but without a formally persisted evidence base. An incident from real application showed that the old usage conditions (`daysSinceIntense ≥ 3` + `TSB > −10` AND-joined) were too restrictive and blanket-blocked strides after a quality double — even though strides are physiologically intended exactly then (Magness, Daniels). Without a research anchor, format decisions continue to drift arbitrarily.

---

## TL;DR

1. **Strides are not a training stimulus, but a neuromuscular maintenance drill.** They should NOT fatigue, but maintain motor-unit recruitment + tendon elasticity + running economy — at minimal metabolic cost.
2. **Consensus format:** **4-6 strides × 15-25 s @ 85-95% effort, 60-90 s easy jog or walking rest between, before the cool-down.** All-out sprints and strides > 30 s miss the purpose — they fatigue without increasing the neuromuscular benefit.
3. **Frequency:** **2-3×/week** is the consensus dosing. More is possible, but brings no additional effect; less and one loses the adaptation within ~10-14 days.
4. **When to insert — primary slots:**
   - **Default at the end of an easy/Z2 run ≥ 40 min** (standard application, no recovery cost).
   - **Before tempo/interval sessions as a neuromuscular primer** (activation of fast-twitch fibres, PAP effect).
   - **During taper week DO NOT stop** (Magness: "you want to optimize your muscle tension during race week" — strides maintain neuromuscular sharpness without fatiguing).
   - **Last 3 days before competition:** strides stay in (short format, 4×15 s suffices).
5. **Effect evidence:** Paavolainen et al. 1999 (J Appl Physiol) — 9 weeks of explosive-strength training (including stride-like accelerations) replaced 32% of volume and significantly improved 5-km time — with UNCHANGED VO2max. Mechanism: better running economy and higher maximal anaerobic running velocity. Coach literature converges on 2-4% running-economy gain within 4-6 weeks of consistent stride practice.
6. **Stop conditions (only these — everything else = default ON):**
   - Acute lower extremity (Achilles tendinopathy, plantar-fasciitis flare, IT-band acute, hamstring strain)
   - HRV > 10% below baseline AND `hrvForecastLatest.verdict ≠ "expected"`
   - TSB < −15 (accumulated fatigue beyond the day-after-quality window)
   - Long run > 90 min yesterday (aerobic depletion still active)
   - Race within 36 h (save the neuromuscular spark for race day)
   - Athlete override in the session

---

## Question / Trigger

The previous `specialist-endurance.md` spec for strides was:

> When to insert (all conditions must hold):
> - Run type is EASY/Z2 and total duration ≥ 40 min
> - No speed work in the last 3 days (daysSinceIntense ≥ 3)
> - No long run (>60 min) yesterday
> - No lower-extremity injury / restriction
> - TSB not strongly negative (> −10)

In real application it turned out that this AND chain blanket-blocked strides after a quality double — `daysSinceIntense = 1` plus TSB slightly negative prevented inclusion, even though the slot "day after quality" is physiologically exactly the stride slot (Magness, Daniels). The spec was therefore rewritten to default-on (with an explicit stop-conditions table). This research file cements the evidence base for it and gives all stride mentions in the framework a common anchor.

Five concrete questions to be clarified here:

1. What are strides physiologically exactly — and what distinguishes them from sprints, accelerations, hill sprints?
2. Which adaptations result (running economy, neuromuscular, tendon) — and with what evidence quality?
3. Which format is consensus (count, duration, effort, recovery)?
4. How often per week, and in which training context (easy run, before quality, taper)?
5. When NOT — which stop conditions are covered by evidence/practice vs. which are myth?

---

## Findings

### 1. Definition and demarcation

Strides are short, controlled accelerations that are NOT conceived as a training stimulus, but as a **neuromuscular maintenance/activation tool**. Magness (2014, *Science of Running*): "strides are a way to maintain speed during periods of heavy aerobic running as they reinforce good biomechanics and the recruitment of fast twitch muscle fibers."

**Demarcation from related formats:**

| Format | Duration | Effort | Rest | Purpose |
|--------|----------|--------|------|---------|
| **Strides** | 15-25 s | 85-95% (controlled) | 60-90 s Z1 jog/walk | Neuromuscular activation, tendon elasticity, running economy |
| **Sprints / Repetition (R)** | 200-400 m, 30-90 s | near Mile pace | ≥ 1:1 rest | Anaerobic capacity, speed endurance |
| **Hill Sprints** | 5-10 s | all-out | 2-3 min full walking rest | Maximum strength, neuromuscular (see [hill-repeats.md](hill-repeats.md)) |
| **Accelerations / Speed Drills** | variable | variable | variable | Umbrella term, often used synonymously with strides — terminology drifts |

Daniels (2013, 3rd ed.) places strides as "roughly the same pace as Repetition (R) pace … 1500m or Mile race pace" — i.e. *not* all-out, but a pace the athlete could hold for 4-5 minutes continuously. Over 15-25 s that is loose, fast running — no torture.

**Frequent error in athlete practice:** strides are run as all-out sprints (90% of hobby runners do this per coach consensus), which misses the purpose — all-out costs recovery (hamstring risk, CNS load) and delivers no greater neuromuscular effect than 85-95%.

### 2. Adaptation mechanisms

**Three adaptation levels are consistently named in the literature:**

#### (a) Motor-unit recruitment and fibre-type maintenance

Endurance training (especially low intensity) shifts the fibre-type profile toward Type I (slow-twitch). Without periodic high-intensity stimuli, the runner gradually loses the ability to effectively recruit Type IIa fibres (fast-twitch oxidative) — which shows up as a flat race-pace ceiling and worse finishing kick.

Strides deliver this stimulus "under the radar" — short enough to produce no recovery cost, fast enough to keep fast-twitch recruitment awake. Magness: "Before workouts, strides make a great neuromuscular primer … activating your fast-twitch muscle fibers and preparing your body to handle higher speeds during the workout."

#### (b) Tendon elasticity and stiffness regulation

Fast accelerations activate the stretch-shortening cycle (SSC) — the short-term elastic-energy storage in the Achilles tendon, patellar tendon and plantar fascia. This SSC function is central to running economy; without periodic activation, tendon stiffness drops and with it the energy return per step.

A 2024 review (Scandinavian J Med Sci Sports, Chalitsios et al.) describes how stride characteristics (ground contact time, knee stiffness) adapt as a function of muscle oxygen supply and degrade under fatigue — i.e. stride mechanics are trainable and losable.

#### (c) Running economy (RE) — the operative adaptation

Running economy = O2 demand at a given submaximal pace. A RE gain of 2-4% corresponds (approximately) to a race-pace improvement of the same magnitude at equal VO2max.

**Strongest evidence: Paavolainen et al. 1999** (J Appl Physiol 86(5): 1527-1533). 10 trained endurance athletes replaced for 9 weeks **32%** of their volume with explosive-strength training (jump drills, sprints, stride-like accelerations, light plyo). Control group (n=8) did 3% of the same content.

> "The 5K time, running economy, and maximal anaerobic running velocity improved in the experimental group, but no changes were observed in the control group … improved 5K time in well-trained endurance athletes without changes in their VO2max, due to improved neuromuscular characteristics."

The punchline: VO2max stayed the same — the improvement came entirely from running economy + maximal strength. Strides are the narrow-gauge analogue: same mechanism, much smaller dose, embedded in ongoing training.

**Coach literature converges** on 2-4% RE gain within 4-6 weeks of consistent stride practice (RunnersConnect, dlakecreates, geeksonfeet — cross-cited without primary RCT). This is plausible, but not as hard as the Paavolainen finding — cautious reading: strides deliver the effect that Paavolainen showed in full dose, in a practical mini-dose.

### 3. Format parametrisation

| Parameter | Standard range | Background |
|-----------|----------------|------------|
| Count | 4-6 (standard) | Enough for stimulus, few enough for 0 recovery cost. In build phase 4×, in maintenance 6× |
| Duration/rep | 15-25 s | Consensus. Magness 15-30 s, Daniels "several seconds", RunnersConnect 15-20 s. Over 30 s the format shifts toward acceleration interval |
| Effort | 85-95% | Magness explicit. NOT all-out. Daniels: Mile pace. If you could hold the pace 4-5 min, it's right |
| Rest | 60-90 s | Z1 jog OR walking rest (both equivalent, Magness/RunnersConnect/Daniels). Fully recovered before next rep |
| Surface | Preferably soft | Forest path, track, grass — asphalt OK, but spare with Achilles/plantar history |
| Placement | Before cool-down (at the end of the easy session) | Stimulus falls on awake legs, cool-down afterwards tidies up |

### 4. Frequency and weekly distribution

**Consensus: 2-3 sessions per week with strides.** RunnersConnect, dlakecreates, geeksonfeet, Magness — all name 2-3×.

**Loss without:** studies on detraining speed (neuromuscular adaptations) show that power and recruitment patterns drop noticeably within **10-14 days** without stimulus. A stride-free period > 2 weeks reduces the later re-entry effect.

**Three canonical slots in the microcycle (for a 3-quality athlete per week):**

| Slot | When | Effect |
|------|------|--------|
| Easy Z2 finisher (default) | At the end of an aerobic-base run ≥ 40 min | Maintenance, no recovery cost |
| Pre-workout primer | Before tempo/interval (3-5 strides after WU drills) | Neuromuscular activation, PAP preparation |
| Taper / race-week maintenance | In every easy session of the taper week | Maintain sharpness without costing glycogen or CNS |

### 5. When NO strides — stop conditions

The old spec said "daysSinceIntense ≥ 3 AND TSB > −10". Both are over-restrictive:

- **`daysSinceIntense` alone is NOT a stop reason.** Strides on the day after a threshold session are exactly the use case that Magness and Daniels mean. Quality double (threshold run Sat + bike VO2max Sat) → strides on Sunday Z2 is textbook.
- **TSB > −10 is too narrow** — daily form and HRV deliver better real-time signals than the ATL/CTL lag of TSB.

**Evidence-based stop list:**

| Stop condition | Reason |
|----------------|--------|
| Acute lower extremity (Achilles tendinopathy, plantar-fascia flare, IT-band acute, hamstring strain) | Stride pace stresses healing tissue |
| HRV > 10% below baseline **AND** `hrvForecastLatest.verdict ≠ "expected"` | Unexplained autonomic load — do not stack a neuromuscular stimulus |
| TSB < −15 | Accumulated fatigue beyond day-after-quality |
| Long run > 90 min yesterday | Aerobic depletion still active, stride form suffers |
| Race within 36 h | Save the neuromuscular spark for race — short strides race-day-WU OK, on the day before NO new stimulus |
| Athlete override in the session | Principal override |

**Myths that do NOT count as stop conditions:**
- "HRV slightly below baseline" — if `verdict = expected` (e.g. after quality stimulus), no stop
- "TSB negative" — between −15 and 0 stride default is ON
- "Strides on the day after quality are too much" — empirically wrong (Magness/Daniels: that is exactly the slot)
- "Strides must be all-out to work" — wrong, 85-95% is optimal

---

## Primary sources

- **Paavolainen, L., Häkkinen, K., Hämäläinen, I., Nummela, A., & Rusko, H. (1999).** "Explosive-strength training improves 5-km running time by improving running economy and muscle power." *Journal of Applied Physiology*, 86(5), 1527-1533. — Hardest primary source for the RE mechanism (5K time ↑ without VO2max change in 9 weeks). https://journals.physiology.org/doi/full/10.1152/jappl.1999.86.5.1527
- **Magness, S. (2014).** *The Science of Running.* Origin Press. — Stride definition, 15-30 s @ 85-95%, "neuromuscular primer", taper recommendation ("optimize muscle tension during race week"). https://magstraining.tripod.com/training.html
- **Daniels, J. (2013).** *Daniels' Running Formula* (3rd ed.). Human Kinetics. — Stride pace = R pace (Mile pace), 5 strides after WU, Wed/Thu/Fri slots. https://static1.squarespace.com/static/5ee7adf2d2607b6317b264a2/t/646395e31537db2f0c2de367/1684248037207/Jack+Daniels+-+Daniels'+Running+Formula-Human+Kinetics+(2021)+reduced.pdf
- **Chalitsios, C. et al. (2024).** "Mechanical Deviations in Stride Characteristics During Running in the … " *Scandinavian J Med Sci Sports*, 34, e14709. — Stride mechanics under fatigue, tendon/stiffness adaptation as a trainable quality. https://kinvent.com/wp-content/uploads/2025/08/Scandinavian-Med-Sci-Sports-2024-Chalitsios-Mechanical-Deviations-in-Stride-Characteristics-During-Running-in-the.pdf

**Secondary sources (coach consensus, well cross-cited):**
- RunnersConnect — "How to Do Strides: Technique, Workouts, and When to Add Them to Your Training" (4-8 reps, 2-3×/week, after easy run). https://runnersconnect.net/how-to-do-strides/
- Strength Running — "Race Faster by Recruiting More Muscle Fibers (the 'Muscle Approach')" (fibre-type maintenance). https://strengthrunning.com/2025/08/muscle-fiber-recruitment/
- geeksonfeet — "Strides: The Secret Weapon for Long-Distance Runners" (format consensus). https://geeksonfeet.com/run/strides/
- dlakecreates — "90% of Runners Do Strides Wrong" (frequent format errors, RE gain 3-4%). https://dlakecreates.com/how-to-do-strides-running/
- Trail Runner Magazine — "Why And How To Run Strides To Improve Speed On The Trails" (strides on trail surface, neuromuscular specificity). https://www.trailrunnermag.com/training/trail-tips-training/

---

## Application in framework

This research is the anchor for the following framework places — all of them mention strides, all must remain consistent with this doc:

| File | What's there | Consistency status |
|------|---------------|--------------------|
| `framework/agents/specialist-endurance.md` § "Strides — default finisher after a Z2 run" | Default-on logic, 4-6× 15-25 s @ 85-95%, 60-90 s jog/walk rest, stop-conditions table | ✅ consistent (default-on spec) |
| `framework/config.example/training_paradigms.md` § "Neuromuscular activation before sessions" (lines 319-323) | Strides before intervals/tempo OR plyo, equivalent — before flat Z2 strides sufficient | ✅ consistent — should link to this doc |
| `framework/config.example/training_paradigms.md` § Trail (line 264) "Strides on uneven surface ≥ 1×/week in the last 4-6 weeks before a trail race" | Specificity adaptation trail | ✅ consistent |
| `framework/config.example/training_paradigms.md` § Taper (line 273) "Last 3 days: Z1-Z2 only, short strides ok" | Strides stay in the taper | ✅ consistent — Magness line |
| `framework/config.example/training_paradigms.md` § Achilles (line 452) "Uphill strides (4-6×40m) deliberately reinstated once the Achilles tendon gives the green light" | Achilles-specific stride re-entry | ✅ consistent |
| `framework/agents/strava-publisher.md` | Stride detection in activity insights | ✅ consistent (read-only) |
| `framework/agents/data-scientist.md` | Strides as lap-pattern detection | ✅ consistent (read-only) |

**Cross-link obligation:** if a specialist or planner in future changes the stride dose (count, duration, effort), loosens/tightens stop conditions, or introduces a new stride slot — READ this document, document the change here, only then apply (cf. CLAUDE.md → "Research-before-scaling-or-new-protocol").

---

## Open questions / Caveats

- **Hill strides vs. flat strides — a direct RE comparison is missing.** Uphill strides are recommended in the trail/Achilles re-entry context (see Achilles §452), but whether they have more/less RE effect per second than flat strides is not primarily-literarily clarified. Practice assumption: hill strides additionally deliver maximum strength (cross-effect with [hill-repeats.md](hill-repeats.md)), at comparable recruitment stimulus.
- **Optimum count per week for trail specialists.** Magness/Daniels targets come from road/track endurance. Trail runners with a high vertical share already get stride-like stimuli through uphill sections — whether additional dedicated flat strides act additively or are overkill is open.
- **Strides + plyo on the same day.** When both serve as a neuromuscular stimulus, the question is unresolved whether the effects add or compete. Practice rule of thumb (Magness): do not combine in the same session, spread across different days or one as primer and the other as standalone block.
- **Stride form drift with age / under high volume.** Studies on stride mechanics under chronic volume load (Chalitsios 2024) show mechanics shifts — the practical conclusion for stride prescription (form-check frequency, cue selection) is not yet derivable from the literature.
- **Distance- vs. time anchor.** Classical coach prescriptions mix "80-100 m" with "15-25 s". Both fix the same rep range (15-25 s ≈ 80-150 m depending on pace), but for the intervals.icu syntax the time anchor (seconds) MUST be used (see memory `feedback_intervals_icu_distance_format` — `100m` would be misinterpreted by the parser as 100 minutes).
