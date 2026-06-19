# Training paradigms & rules

> **Framework defaults.** This file describes generic training theory
> (polarized / pyramidal, intensity control, trail / ninja peaking, tag
> system). Concrete BPM values or athlete-specific examples (injury
> blocks, weekly templates) live in `config/athlete_status.md`,
> `config/athlete_static.md` and the wrapper version of this file.
> Athlete-specific content in `config/training_paradigms.md` overrides
> the defaults defined here via the loader fallback
> (`CONFIG_DIR → CONFIG_FALLBACK`).

## HR zones
The heart-rate zones are loaded dynamically from intervals.icu and are
available as `{hr_zones}` in prompts.

**Research anchor:** [HRV & RHR baseline — methodology, LTHR derivation](../research/hrv-rhr-baseline-methodology.md)

## Polarized training (build phase)
- 80 % of sessions in Z1–Z2 (easy)
- 20 % in Z4–Z5 (hard)
- Z3 is actively avoided
- After 2–3 consecutive easy sessions a hard session can follow,
  provided HRV ≥ baseline and TSB > −5
- HRV ≥ baseline and TSB > 0 = green light for intensity

**Sources:** Seiler 2010 (*Int J Sports Physiol Perform*) — observational
analysis of elite endurance athletes converging on a ~80/20 distribution;
Stöggl & Sperlich 2014 (*Front Physiol*) — RCT showing polarized > threshold/
high-volume/HIT in trained endurance athletes; Stöggl & Sperlich 2015
(*Front Physiol*) — meta-review.

**Research anchor:** [Polarized training — Seiler 80/20, RCT evidence](../research/polarized-training-seiler.md)

## Pyramidal training (8–10 weeks before competition)
- 70–80 % in Z1–Z2 (easy)
- 15–20 % in Z3–Z4 (moderate / threshold)
- 5–10 % in Z5 (high intensity)
- Z3 and Z4 are trained deliberately (not avoided), often as tempo runs
  or threshold intervals
- After 2–3 easy sessions a threshold or high-intensity session can
  follow, provided HRV ≥ baseline and TSB > −5
- HRV ≥ baseline and TSB > 0 = green light for race-specific intensity
  (e.g. 10K, half marathon)

**Sources:** Treff et al. 2019 (*Eur J Sport Sci*) — pyramidal vs polarized
in rowing; Casado et al. 2022 (*J Strength Cond Res*) — pyramidal effective
for sub-elite distance runners in marathon prep.

**CTL threshold for switching modes:**
- Default: CTL ≥ 50 (sufficient volume base for threshold work)
- Adjusted (in-season build-up): CTL ≥ 35 is enough when race distance
  ≤ half marathon and a peak CTL is realistically unreachable
- B races (e.g. mid-season trails): no switch — race on current form,
  stay polarized

**Sources:** Coggan & Allen 2019, *Training and Racing with a Power
Meter* (3rd ed.) — Performance Manager Chart, CTL/ATL/TSB framework.

**Research anchor:** [Pyramidal distribution — evidence, Treff & Casado](../research/pyramidal-distribution.md)

## Intensity control
- TSB < −20: immediate reduction to Z1 or rest day (mandatory, even if
  the plan says otherwise)
- TSB > 0 + HRV ≥ baseline: green light for intensity

**Sources:** Bourdon et al. 2017 (*Int J Sports Physiol Perform*) —
fatigue / freshness monitoring with TSB; Bellenger et al. 2016 (*Sports
Med*) — HRV as a recovery proxy in endurance athletes.

## Pace / GAP — source hierarchy for run analysis (MANDATORY)

For every run analysis with a hilly profile (>30 m elevation gain / km),
Grade-Adjusted Pace (GAP) MUST be evaluated instead of avg-pace alone —
otherwise uphill / downhill segments distort the efficiency assessment
in both directions (uphill-slow is praised as "too slow", downhill-fast
is read as "particularly efficient"). FIT-lap elevation values are
routinely distorted by GPS drift — another reason to use GAP rather
than a naive pace × elevation mix.

**Source hierarchy (best → worst for pace / GAP analysis):**

| Source | avg-pace | Native GAP | Distance smoothing | Use |
|--------|----------|-----------|--------------------|-----|
| **Strava** | smoothed | ✓ native | ✓ (typically +5%) | **Canonical for GAP** — industry-established algorithms |
| **intervals.icu** | raw FIT | optional (`gap_model`) | no | Secondary source; GAP only if sport setting is enabled |
| **Garmin Connect** | raw FIT | ✗ (Connect-IQ third-party only) | no | Good for raw pace, no GAP |

**Operational rule (head coach + specialists):**
- Run analysis with elevation (≥30 m/km) → **Strava GAP** as the primary
  pace reference
- Raw FIT pace (intervals.icu default) only as a secondary value, never
  as a sole efficiency statement
- On discrepancy Strava vs. intervals.icu (distance +5%, pace −15 s/km
  typical): treat Strava as canonical, name the intervals.icu delta
  explicitly in the analysis ("Strava smoothing differs")
- Always distrust FIT-lap elevation — on conflict with the activity
  summary (intervals.icu `total_elevation_gain`), follow the activity
  summary
- Pace praise in coaching feedback ONLY when GAP + HR together support
  it, not avg-pace alone

**Typical drift patterns that motivate this rule:**
- Z2 run on a hilly forest path; avg-pace gets praised as "economical"
  while FIT-lap-ascent is GPS-drift-inflated, GAP is significantly
  stretched against avg-pace, and the downhill share inflates the avg
  number.
- Brick Z2 on a forest path; intervals.icu avg-pace and intervals.icu
  GAP are cited — Strava returns clearly different values (typically
  15–20 s/km delta due to GPS smoothing); the athlete spots the gap
  empirically by comparing the two views.
- Takeaway: Strava GAP is the canonical source for any pace assessment
  involving elevation.

**Research anchor:** [Strava vs. intervals.icu GAP — algorithm differences & canonicity](../research/strava-vs-intervals-gap.md)

## HRV readiness (`hrvReadiness` — 7d-rolling ln-rMSSD vs 60d normal band)

`fetch_context.py` provides the top-level field `hrvReadiness`: the 7-day
rolling mean of ln-rMSSD classified against a 60-day normal band (mean ±
0.5·SD of the daily values). Replaces the retired load→HRV forecast — load
is no longer a predictor, only a parallel CTL/TSB stream.

**Fields:**
- `verdict`: `clear` | `above` | `watch` | `hold` | `insufficient_data`
- `days_below`: consecutive days the rolling mean is below the band
- `rolling_mean_ms`, `band_low_ms`, `band_high_ms`: 7d mean + band (back-transformed)
- `cv`, `n_ref`: within-athlete CV + valid daily values in the 60-day window

**Rules for planner / specialists:**
- `clear` → rolling mean inside the normal band, continue the planned stimulus
- `above` → above the band, good recovery/adaptation; a slight bump is fine
  if other signals agree
- `watch` → 1–2 days below band, soft signal: proceed, note it in
  `coaching_notes`, ask about confounders
- `hold` → 3+ consecutive days below band, hard signal: recovery is the
  default (aligned with the combined HRV+RHR overload trigger)
- `insufficient_data` → <30 valid daily values in the 60-day window: band
  not computable, fall back to the 90d-median+5% logic; **neither** green
  light **nor** red flag
- Look at multi-day patterns, do not overinterpret single values

**Advisory field `hrvCvTrend`:** day-to-day CV trend
(`rising`/`stable`/`falling`) as an early non-functional-overreaching hint
(Plews 2012) — informational only, **not** a hard trigger.

**Top-level field `hrvReviewPending`:** set when `hrvReadiness.verdict` is
`watch`/`hold` and no `HRV-Review` NOTE yet covers the below-band window.
Head coach asks the athlete during `/wellness` or `/training` (once per
day) about external factors.

## Cool-down after intense sessions

- **Goal:** active lactate clearance — no HR target, no shuffling
- **Tempo:** easy running at "comfortable" feel, even if HR is still in
  the Z2 range
- **Don't:** force HR below the individual Z1 ceiling by going extremely
  slow — that degrades biomechanics without added benefit
- **Duration:** 10–15 min; HR drops into Z1 physiologically on its own
  once the body has recovered
- **intervals.icu format:** cool-down as a pace step (e.g. "10min easy") —
  no HR-zone target (same principle as warm-up)
- **For analysis:** high GCT during cool-down is normal (slow tempo =
  higher GCT), not a fatigue indicator per se

## Cardiovascular startup (cardiac drift)
- During the first ~10 minutes of a run, HR rises with a physiological
  delay (cardiac output lag)
- **Warm-up in intervals.icu format: no HR-zone target** — otherwise the
  watch triggers a false alarm even though pace and effort are correct
- HR orientation for the athlete may stand in the description text, but
  never as a zone target in the workout step
- For analysis: ignore the first 10 minutes of a run in HR evaluation

## Warm-up priming before quality sessions

A pure easy Z1–Z2 warm-up does NOT prime VO2 on-kinetics. Without
progressive heavy spikes the first work reps run under a slow
primary-VO2 response and fall below the time-above-90 %-VO2max band —
which for short-rep formats (30/15, 30/30) is the whole stimulus. Every
quality warm-up therefore ends with priming spikes before the first work
rep.

Generic template (after the easy build):

- Easy build: **10–15 min Z1–Z2**.
- Heavy spikes: **2–3 × 60–90 s heavy** (bike ~90–100 % FTP / ~85 % MAP;
  run ~CV / threshold pace), **60–90 s easy** between.
- Optional neuromuscular touch: **3–5 × 10–15 s** brisk (bike sprint at
  moderate cadence; run stride).
- **Rest before the first work rep: 3–10 min easy** (shorter → residual
  fatigue, longer → the VO2-kinetic effect decays).

Necessity by session class: **VO2max short (30/15, 30/30) → MANDATORY**;
**VO2max long (4×4, 5×3) → recommended**; **Threshold (Z4) → optional**
(one submaximal 2–3 min build into threshold pace suffices); **Easy /
Recovery / Long → none** (end-of-easy-run strides remain a separate tool
for the *next* quality day, see `strides-protocol.md`). On the bike the
spikes carry a **watt** target, not HR-only. Mechanical enforcement:
`validate_plan.py::check_quality_warmup_priming` (R019) warns when a
short-rep VO2max session has no warm-up spike.

**Research anchor:** [Warm-up priming before intervals](../research/warmup-priming-intervals.md)

## Zone validation with Polar H10 (DFA-α1 method)

If zones are uncertain (see triggers below), the athlete is advised at
the next Z2 run to wear an **RR-capable chest strap** (e.g. Polar H10)
instead of a wrist / optical HR sensor. With such a sensor DFA-α1
(Detrended Fluctuation Analysis) lets the aerobic (VT1) and anaerobic
threshold (VT2 / LTHR) be validated in training.

**Science:** DFA-α1 = 0.75 → VT1 (±4–7 bpm accuracy, r > 0.88); DFA-α1
= 0.5 → VT2 / LTHR (r ≈ 0.85). Both thresholds capturable in a single
run (Rogers et al. 2021, Doerr et al. 2021).

**Triggers for H10 recommendation** (one is enough):
- Last zone validation (`lastZoneValidation` in `athlete_status.md`)
  > 10 weeks ago
- Training break > 3 weeks (implicit threshold drift)
- CTL growth > 15 % since last validation
- Athlete reports: "Z2 feels too easy / too hard"
- Rebuild after injury / illness (> 2 weeks off)

**Test protocol (for coach-analyst or planner hint):**
1. Put on an RR-capable chest strap, wet electrodes 10–15 min before
   the test
2. DFA-α1 live app (e.g. Fatmaxxer on Android/iOS) → connect strap via
   BLE → DFA-α1 displayed live
3. Run: 10 min easy Z1, then every 3–5 min raise pace by ~10 s/km until
   above LTHR
4. DFA-α1 = 0.75: aerobic threshold (new Z2 ceiling); DFA-α1 = 0.5:
   LTHR (new Z4 ceiling)
5. Post-hoc analysis: export RR data from the strap app → Kubios HRV
   (free) for precise evaluation

**When to repeat:** every 8–10 weeks, after breaks > 3 weeks, after a
CTL jump > 15 %.

**Research anchor:** [DFA-α1 — VT estimation from HRV, Rogers / Doerr protocol](../research/dfa-alpha1-vt-estimation.md)

## Cross-training periodisation — 2 hard stimuli per week with bike decoupling

**When to apply:** as soon as CTL ≥ 20 and the athlete tolerates one
more training stimulus per week than a single run threshold block —
typically during the rebuild after a polarisation deficit (hard share
< 15 %).

### Strategy
- **Stimulus 1:** run threshold (Z4) — sport-specific, 1×/week, typically
  Tuesday or Thursday
- **Stimulus 2:** bike VO2max (Z5) — cross-training, 1×/week, typically
  Saturday
- **Rationale:** two metabolic stimuli per week raise the hard share
  without both producing run impact. The bike decouples the VO2max
  stimulus from run impact → spares Achilles, knees and running legs.
  Run-VO2max transfer from cycling is ~50–70 % (suboptimal but
  metabolically valid).
- **At least one easy day between hard days** (Z1/Z2 or full recovery).

**Research anchor:** [Cross-training VO2max transfer — bike → run, 2-stimulus strategy](../research/cross-training-vo2max-transfer.md)

### Brick run after bike VO2max — MANDATORY when feasible
Right after the bike block, add a 20–60 min easy run. Trains:
- Running economy on pre-fatigued legs (neuromuscular bike → run
  switchover)
- Specific running adaptation that a pure bike stimulus does not deliver
- Lipid oxidation in a pre-loaded muscle metabolism
- Closes the sport-specificity gap vs. a pure run long-run

**Intensity choice by brick purpose:**
- **Long-run simulation (40–60 min brick):** **Z2** (aerobic base, lipid
  oxidation, classical long-run intensity on pre-fatigued legs). Pace
  leads — cardiac drift after the bike is normal, HR in Z2/Z3 is
  physiological. Source: 80/20 triathlon method + classical triathlon
  training literature for endurance bricks.
- **Recovery brick (15–25 min brick):** Z1 (easy, neuromuscular
  switchover, no metabolic stimulus).
- **Race-pace brick (race prep):** Z3 / T-pace, sport-specific stimulus.

NO tempo push, NO ramp-up in the second half — not even at Z2. A
blanket-Z1 rule is too conservative; for a long-sim, HR-pacing in Z1
(due to drift) misses the stimulus and forces a crawl.

**Research anchor:** [Brick running intensity — Z2 vs. Z1 after bike block](../research/brick-running-intensity.md)

### VO2max format choice (bike) — evidence over tradition

Classical 4–5×5min or 5×3min Z5 is robust and easy to pace, but not
optimal for trained cyclists from a sport-science standpoint. From
CTL ≥ 20 onwards and for athletes with ≥3 years of structured endurance
experience, **short intervals (Rønnestad 30/15 or Billat 30/30)** are
evidence-based superior for pure VO2max accumulation:

| Format | Effective time ≥90 % VO2max | Complexity | Ideal for |
|---|---|---|---|
| 4–5×5min Z5 (Helgerud classic) | ~10–12 min | low | First stimulus, pace finding, build phase |
| **5×3min Z5** | ~8–10 min | low | Compromise format during rebuild |
| **Rønnestad 30/15** (3×13×30s/15s) | ~13–15 min | medium (pacing discipline) | Trained cyclists, deep build |
| **Billat 30/30** (8–12×30s/30s) | ~7–8 min | low (simple pacing) | Build, variation, short time |

**Evidence:** Rønnestad & Hansen 2015 — 3×13×30/15 vs. 4×5min: +5 % FTP
gain in 10 weeks, more time ≥90 % VO2max. Billat 1999 — 30/30 reaches
~7:51 min @ VO2max vs. 2:42 min at continuous tempo. Caveat (Skovgaard
et al, Frontiers 2024): if short intervals are "intensified" (>MAP),
time ≥90 % VO2max drops from 5.5 to 3.4 min — worse, not better.

**IMPORTANT — power zone for 30s reps:**

The correct intensity for 30s reps in the 30/15 Rønnestad format is
**~100 % MAP** (Maximum Aerobic Power = lowest power that just elicits
VO2max, ~5-min peak power). MAP in trained cyclists typically equals
**105–120 % FTP**, not 130–145 % FTP. Earlier versions of this document
had 130–145 % FTP as the 30/15 target — that was a mix-up with
anaerobic-capacity zones. Background + primary sources:
[`framework/research/vo2max-short-intervals.md`](../research/vo2max-short-intervals.md).

Concretely:
- **30/15 Rønnestad 30s power: ~100 % MAP, individually 105–120 % FTP**
  (validate the watt anchor via actually completed prior sessions, not
  a pure FTP multiplier). MAP-default estimate when unmeasurable:
  FTP × 1.15.
- **15s rest: ~50 % MAP** (easy spinning, not full recovery)
- **5-min VO2max power (3–5 min intervals):** 95–105 % MAP / 110–120 %
  FTP
- **Pure anaerobic-capacity sessions** (30s all-out, Wingate-style):
  130–145 % FTP — different format, not 30/15

**Common mistake:** running 30s reps in the 30/15 format at 130 %+ FTP
= "intensified short intervals" per Skovgaard 2024 = LESS time above
90 % VO2max, not more.

**Watt-anchor validation via history + compliance obligation:** before
repeating an interval format, read `interval_summary`, `compliance`,
`decoupling` of the most recent same-format session. On compliance
< 95 % OR decoupling > 10 %: reduce volume AND/OR intensity, NEVER
repeat 1:1.

**Volume scaling by CTL/TSB AND compliance history:**
- CTL ≥ 30 or fully recovered, previous session fully completable:
  3×13×30/15 or 12×30/30
- CTL 20–30 or TSB negative, previous session clean at a smaller
  format: 2×13×30/15 or 8–10×30/30
- CTL < 20 or first stimulus after a break: 5×3min classic (more
  robust, less pacing risk)
- **Rebuild after compliance incident (<95 % previous session):**
  **3×8×30/15 @ MAP range** as re-entry (Coach Ben re-entry "2–3×9 @
  110 % threshold", chosen more conservatively). Three shorter sets
  allow 2× 3-min set pauses → cardiac reset → higher completion
  probability. At equal total-rep budget, empirically: **3×8 > 2×12 >
  1×24** when compliance is fragile.

**Pacing cues WITHOUT a power meter (or under uncertain
power–VO2max correlation):**

Subjective:
- 30s hard phase: "could just hold 30s, but not 45s" — RPE 8.5–9
- Breathing: clearly elevated after 5–10 s, "not speak-capable" at the
  end of the 30s
- Legs: burn noticeably at the end of the 30s; rest barely long enough
  to recover — by design
- Cadence: 90–100 rpm, NO big drop in the 30s — if rpm drops > 15, it
  was too hard

HR signals (delayed at short intervals — not for 1:1 pacing control):
- Reps 1–3: HR typically rises into Z3/Z4 — **that is normal, not too
  little**
- Reps 4–8: HR reaches Z5
- Reps 9–13: HR at max (should stay ≤95 % HRmax)
- HR not yet in Z4/Z5 after rep 5 → intensity UP
- HR already at max after rep 3 → too hard, intensity DOWN
- HR plateaus high + legs fail + rpm drop > 15 → abort the set,
  stimulus was sufficient

Across sets:
- If set 1 holds cleanly and set 2 becomes impossible after rep 5 → 2
  sets is the ceiling, not 3
- If both sets are "controlled hard" — next time raise intensity +5 %
  or consider a 3rd set

**Research anchor:** [VO2max short intervals — 30/15 format, MAP & time ≥90 % VO2max](../research/vo2max-short-intervals.md) | [MAP & FTP — ramp-test methodology](../research/map-ftp-ramp-test.md)

### What NOT to combine

| Block A | Block B | Reason |
|---|---|---|
| **Plyo + bike VO2max** | same day | Both fast muscular structures — double maximal stress, leg structures overloaded |
| **Threshold run + bike VO2max** | same day | Double metabolic peak, recovery damage |
| **Long run + bike VO2max** | same day | Volume × intensity = quad/glute hammer |
| **Bike VO2max + heavy leg strength** | same day | Quads/glutes completely flat |

Plyo belongs either on an easy run day (gently integrated) or on the
day BEFORE the next recovery day.

### Weekly example (CTL ≥ 20, rebuild, polarisation step)
| Day | Content |
|---|---|
| Mon | Mobility / rehab (when routines from `athlete_static.md` risk-zone listings apply) + Pull/Core, plyo if fresh |
| Tue | Easy run Z2 + complementary |
| Wed | Recovery or mobility |
| Thu | **Threshold run** (Z4 5×4 or 5×5) + light complementary activation |
| Fri | Easy run Z1/Z2 + Core/Grip — NO plyo (leg recovery) |
| Sat | **Bike VO2max** (Rønnestad 2–3×13×30/15 or Billat 30/30 by CTL) + 40–60 min brick run Z2 (long-sim) or 20–30 min Z1 (recovery brick) + mobility / rehab |
| Sun | Long Z2 OR recovery bike Z1 (passive recovery, high Z1 volume for polarisation) |

## Trail-specific training

Applies when the race calendar contains trail races (indicator:
`type=Trail`/`Waldlauf` in `competition_plan.md`).

### Intensity blocks
- **Uphill Z4** replaces classical tempo runs: 4–6 × 2–4 min uphill at
  Z4 intensity, walk recovery downhill
- **Downhill technique** as its own block 1×/week: controlled downhill
  running, focus on short ground-contact time and upright posture
  (eccentric quad loading as trail preparation)
- Strides on uneven ground ≥ 1×/week in the last 4–6 weeks before a
  trail race

**Research anchor:** [Hill repeats — uphill intervals, intensity & adaptation](../research/hill-repeats.md)

### Complementary adjustment for trail
- Raise plyo and leg frequency: 3×/week instead of 2× (higher impact
  load downhill)
- Prioritise single-leg exercises (pistol squat, step-up, single-leg
  RDL) for downhill stability
- Increase balance training (trails = uneven ground)

### Tapering trail race
- Last 7 days: drop the downhill block (DOMS risk)
- Last 3 days: only Z1–Z2, short strides ok
- Target TSB: +5 to +15 (same as road)

**Research anchor:** [Downhill running DOMS & taper — downhill block in the last 7d](../research/downhill-running-doms-taper.md)

## Ninja pillars — rotation & cross-pillar locks

The five pillars: **Core**, **Grip**, **Pull** (upperbody), **Push**
(upperbody), **Explosive Power** (plyo). Active phase locks (push block,
achilles phase, etc.) live in `config/athlete_static.md`.

**Cross-pillar locks (next day):**
- **Grip → Pull: locked on the following day** — exhausted forearm
  flexors compromise scapular stabilisation during rowing and sabotage
  any pull-rehab protocol. Pull → Grip on the next day is permitted.
  *Implementation note:* `recovery.py` triggers the lock for the entire
  `upperbody` tag (Pull **and** Push), because the tag system currently
  carries no pull/push distinction. Push is therefore conservatively
  co-locked — not strictly required (Push has no forearm-flexor draw),
  but rarely a problem in practice since Push is typically constrained
  in parallel via a shoulder restriction in `athlete_static.md`.
  Granular separation possible later by extending `VALID_TAGS` with
  separate `pull` / `push`.
- **Never the same pillar on two consecutive days** — independent of
  whether a ⛔ lock is active.

Tags from the last Ninja session must NOT repeat in today's workout
tags. Example: yesterday `["ninja", "core"]` → today no `core` tag, use
`grip` or `upperbody` instead.

## Ninja peaking (before competitions with Ninja elements)

### 3–4 weeks before a Ninja competition
- Raise grip volume: Farmer's Walk, Towel Grip, finger extensors
  lightly daily
- Pillar focus: Grip + Pull (scapular stability) + Core (L-Sit, Hollow
  Hold) — Push only if `athlete_static.md` risk-zones list no lockout
- Drill specific movement patterns: obstacle transfers, Laché
  simulation when feasible

### 1 week before a Ninja competition
- No new volume, no new exercises
- Activation only: short grip sets, scapular mobilisation, core holds
  (Hollow Hold 3×20s)
- Ninja upper body locked from `raceInDays ≤ 2` (CNS + upper-body
  tension)
- Dead Hang: only when no active shoulder / elbow lock is listed in
  `athlete_static.md` — otherwise Towel Grip as a substitute

### Movement clearance after injury
If an active injury in `athlete_static.md` locks a movement pattern
(e.g. overhead hang under a shoulder restriction), clearance runs via
clear functional criteria — not via calendar. Example criteria should
be documented in `config/athlete_static.md` next to the relevant
risk-zone (e.g. "Clearance Dead Hang: pain-free hang at 50 % body
weight for 10s, no clicking").

## Concurrent strength + run interference minimum spacing (double sessions)
**Sources:** Coffey & Hawley (2017), Wilson et al. (2012, MSSE)

For double sessions with WeightTraining + run, the following minimum
spacings apply:
- WeightTraining (general) → run: **≥3h spacing**
- WeightTraining with leg focus (tags: `beine`, `plyo`) → run: **≥6h
  spacing**

Reason: leg strength before a run significantly increases metabolic
interference and CNS fatigue. The spacing enables partial glycogen
resynthesis and reduces mechanical fatigue. **Exception:** pre-fatigue
long-run simulation (Z2 run after moderate leg strength as an
intentional stimulus) — does not apply to quality stimuli
(threshold / VO2max).

**Order:** WeightTraining ALWAYS before the run (same day). Never the
other way round.

**Start times** (`workout_parser.py` applies these automatically):
- Standard double-day: strength 06:00 → run 09:30 (06:00 + strength
  duration + 3h)
- Leg-intensive / plyo + run: strength 06:00 → run 12:30+ (06:00 +
  strength duration + 6h)

**Research anchor:** [Concurrent training interference — strength–run spacing 3h/6h](../research/concurrent-training-interference.md)

## Plyo integration (runners + Ninja)
- As a 5–10 min warm-up block BEFORE a Z2 run: ok (same day, plyo
  first)
- As a stand-alone unit: 48h spacing from intervals
- Long run (>60 min) yesterday: only light plyo as warm-up
- Normal Z2 run yesterday: no obstacle for plyo
- Target frequency: 2–3×/week, 10–20 min is fully sufficient

**Research anchor:** [Plyometrics — frequency, recovery & 48h spacing from intervals](../research/plyometrics-frequency-recovery.md)

## Neuromuscular activation before sessions
- Before intervals / tempo: strides (3–4×) OR a short plyo sequence —
  equivalent for run performance
- Prefer plyo when explosiveness / tendons are a training goal anyway
  (cross prep, Ninja)
- Before flat Z2: strides are sufficient, plyo optional
- Strides at the END of an easy Z2 ≥ 40 min are the default slot — no
  pre-workout obligation
- Format, frequency, stop conditions + evidence: see
  [framework/research/strides-protocol.md](../research/strides-protocol.md)
  (standard: 4–6× 15–25s @ 85–95 % effort, 60–90s jog/walk recovery,
  2–3×/week)

### PAP rule: what is permitted before threshold / VO2max (MANDATORY)

Post-Activation Potentiation works with **short explosive stimuli**, NOT
with heavy eccentric tendon loading. Concretely:

**Permitted before Z4/Z5 sessions** (PAP-positive, may raise pace):
- Pogo Hops 2–3×10–12 RPE 5–6 (light, dynamic, short ground contacts)
- Lateral Bound 2×6–8/side RPE ≤6
- Low Box Jump 2–3×5 RPE 6
- Strides 3–4× 20s
- Drills (A-skips, leg swings, hip-flexor)

**Forbidden before Z4/Z5 sessions** (degrades pace, raises RPE, extends
recovery):
- Eccentric calf raises with load (regardless of +5 kg or +10 kg) —
  deep tendon stimulus
- Goblet Squat / SL RDL with load RPE ≥6
- Heavy heel drop / loaded step-up
- Higher-volume plyo blocks (>30 ground contacts at high intensity)
- General: any strength loading with RPE ≥7 or slow tempo (3-1-X)

**Sources:** Doma & Deakin 2013 (J Strength Cond Res), Healey et al.
2018 (Med Sci Sports Exerc), Tillin & Bishop 2009 (Sports Med review on
PAP). Consensus: light explosive stimuli facilitate, heavy eccentric
loading compromises subsequent running performance within <24h.

**Practical consequence:** when a plyo complementary day precedes a
threshold day, the complementary specialist must restrict the plyo
block to PAP-positive movements only — heavy eccentric rehab exercises
belong on easy / recovery days or as a standalone unit ≥6h before the
run.

**Research anchor:** [Eccentric calf loading before intervals — PAP inhibition](../research/eccentric-calf-pap-inhibition.md)

## Available training types (intervals.icu)
| Type | Fields |
|------|--------|
| Run (outdoor/indoor) | type="Run" |
| Indoor bike | type="Ride", indoor=true |
| Strength/Core/Plyo/Balance | type="WeightTraining", workout_type="STRENGTH" |
| Recovery (foam roller, stretching, mobility) | type="Workout", workout_type="RECOVERY" |
| Rest day | type="Workout", workout_type="RECOVERY", duration_min=0, name="Rest day" |

## Tag system
| Tag | Meaning |
|-----|---------|
| run | Any run unit |
| ride | Any bike unit |
| core | Contains core exercises |
| beine | Leg strength: squats, lunges, RDL, etc. |
| plyo | Jumps, box jumps, explosive |
| balance | Balance board, single-leg stand, slackline |
| mobility | Foam roller, stretching, mobility, recovery |
| intervals | Intervals, threshold units, Z4/Z5 blocks |
| ninja | Ninja-athletics unit (Grip, Upper Body, Ninja-Core, Ninja-Plyo) |
| grip | Grip / forearm training (always with #ninja) |
| upperbody | Upper-body Pull/Push (always with #ninja) — active Push/Pull locks come from `athlete_static.md` |

- `#plyo` = stand-alone plyo unit >15 min (implicitly also `#beine`)
- `#beine` = leg-focused strength without jump character (squats, lunges,
  RDL)
- Plyo as a short warm-up (<10 min) is not tagged
- `#ninja` = stand-alone Ninja session ≥15 min, triggers Ninja
  specialist
- `#ninja #grip` = grip focus (Gripmaster, Farmer's Walk, Towel Grip)
- `#ninja #upperbody` = Pull (Rows, TRX Rows, Face Pulls) + Push
  (Push-ups, Dips); active locks come from `athlete_static.md`
  risk-zones
- `#ninja #core` = Ninja-specific core (Hollow Hold, L-Sit,
  Anti-Rotation)
- `#ninja #plyo` = obstacle-specific explosiveness (Clap Push-ups,
  Laché drills)

**Delineation Ninja vs. complementary:**
| Tag combination | Specialist | Focus |
|-----------------|------------|-------|
| `#core` (without ninja) | Complementary | Running core (Dead Bug, Plank, Bird Dog) |
| `#ninja #core` | Ninja | Ninja core (Hollow Hold, L-Sit, Anti-Rotation) |
| `#plyo` (without ninja) | Complementary | Running plyo (Box Jumps, Bounds) |
| `#ninja #plyo` | Ninja | Obstacle plyo (Clap Push-ups, Laché drills) |

## Complementary units – due-date rules
| Category | Warn (🟡) | Overdue (🔴) |
|----------|-----------|--------------|
| Core | 4d | 6d |
| Beine | 5d | 7d |
| Plyo | 3d | 5d |
| Balance | 5d | 8d |
| Mobility | 3d | 5d |
| Ninja | 2d | 3d |

- Beine/Plyo locked (⛔) when intervals in the last 2d
- After a long run yesterday: only light plyo as warm-up (5–10 min ok)
- Ninja Grip is not locked by intervals (no shared muscle group)
- Ninja Upper Body locked when intervals in the last 1d (CNS recovery)
- Ninja in general is NOT locked by Beine/Plyo (different muscle
  groups)
- Ninja Upper Body locked (⛔) when `raceInDays ≤ 2` (CNS + upper-body
  tension)
- Ninja Grip: `raceInDays ≤ 1` locked; `raceInDays = 2` ok if light
  (Forearm Curl, no Farmer's Walk)

## Ninja integration
- 2–3×/week, 20–30 min standalone
- Minimal interference with running (different muscle groups / energy
  systems)
- ≥6h spacing from hard intervals recommended
- Can be trained on easy / recovery days without issue
- Rotate pillars for variety: Grip → Pull/Push → Core → Plyo → back

## Running-technique drills — standard warm-up (MANDATORY)

**Background:** form-check findings consistently show heel-strike ahead
of centre of mass + incomplete hip extension. Drills belong in every run
warm-up until the next form-check evaluation.

### Warm-up block (3–5 min, before every run):
1. **Hip-flexor mobility** — kneeling lunge, push hips forward, 30s/side
   (shortened hip flexors = cause of hip-extension deficit)
2. **A-skips** — 2×20 m, foot actively pulled under the hip, not in
   front of the body
3. **Leg swings / hip openers** — standing, swing leg backwards until
   the hip fully opens, 10×/side

### Cadence (NO prescription in workouts):

**Decision:** cadence prescriptions removed from run workouts. Rationale
based on the published evidence and the athlete's 10+ years of running
experience:

- **Pace-dependent cadence is physiologically normal** (Quinn et al.
  2019, van Oeveren et al. 2017): trained runners pick their cadence
  pace-specifically and economically — lower cadence at slower paces is
  energetically efficient, not a deficit.
- **Daniels' "180 spm" is a myth** for all paces: Daniels measured 180
  in Olympic runners at race pace, never formulated it as a universal
  prescription.
- **Cadence increase is an injury tool, not a performance tool**
  (Heiderscheit 2011, Bonacci 2018, BJSM): +5–10 % cadence reduces
  knee/hip load — but no transfer of Z2-cadence training to Z3/Z4
  performance is documented.
- **Self-selected ≈ optimal in experienced runners** (Snyder & Farley
  2011): with >5 years of experience, self-selected cadence sits within
  <2 % of the energetic optimum.

**Typical pace–cadence coupling in trained runners:**
- Z2: ~170–180 spm (individual variance)
- Z3: ~180–190 spm
- A pace-dependent rise of ~10–15 spm Z2→Z3 is a physiologically normal
  adaptation pattern, not a deficit.

**Rule for `specialist-endurance`:**
- NO generic cadence prescription in run workouts anymore — not in
  warm-up or Z2 steps either
- EXCEPTIONS where a cadence prescription is still meaningful:
 1. **Strides / cadence drills** as an explicit training purpose
 2. **Acute injury rehab** (knee, hip) — +5 % cadence as the
    Heiderscheit rehab protocol
 3. **Cadence drop below 160 spm** observed in multiple sessions
    (overstride risk)
- **Device cadence range alarms:** when the athlete should not train a
  generic cadence prescription, any cadence alarm on the sport watch
  should be disabled (device-specific in the "Run" activity profile →
  alarms → cadence). Reactivation only during active rehab or observed
  overstride risk (see exceptions above).

**Research anchor:** [Running cadence — 180-spm myth & evidence](../research/running-cadence-myths.md)

### Daily balance routine (permanent)

**Daily as a 3rd unit** — independent of the main plan, existing
workouts are not shortened.
- Rotation A/B/C/D, date-based (`date.toordinal % 4`) — never the same
  session two days in a row
- Duration: 10–12 min | equipment: balance board, TRX, stairs, body
  weight
- Pool: `config/balance_pool.json` | push: `get_balance_rotation.py |
  push_workouts.py`
- No push needed on rest days, but allowed

### Balance exercises: stability rating S1–S5 (instead of RPE)

For balance and proprioception exercises (balance board, single-leg
stand, Bosu, slackline), RPE is not appropriate — the stimulus is
coordination / concentration, not a strength or endurance stimulus. **Use
the stability rating S1–S5:**

| Rating | Description | Progression decision |
|--------|-------------|----------------------|
| S1 | Stable, no wobble | Too easy → make variant harder |
| S2 | Light wobble, no compensating step | Beginner target range |
| S3 | Clear wobble, compensating movements | Advanced target range |
| S4 | Multiple near-limit moments, holds | Borderline, keep brief |
| S5 | Repeatedly fell over / aborted | Too hard → simplify |

**Progression options from S1:** eyes closed → unstable surface →
external load (KB) → combined.
Always state the target S in the description: `Target: S2–S3 for 30s`.

### Run-ABC in balance sessions (explicit block):
- A-skips + leg swings as a 5–8 min block of their own in every balance
  session (not only as a run warm-up)
- Rationale: balance training + run-ABC share the same focus on
  proprioceptive control and single-leg stability
- For `specialist-complementary`: on a balance day always start with a
  run-ABC block (before balance exercises, after the general warm-up)

### Drill progression (next form-check evaluation):
- Next form check at a tempo / interval session (Z3–Z4) — then compare
  whether heel-strike is structural or Z2 shuffle
- Uphill strides (4–6×40 m) used deliberately as soon as the Achilles
  has green light

## Static stretching — guidelines
- **Hold time: 30s per side** (sweet spot per the research; longer holds
  show no documented added value for pure mobility maintenance)
- Maximum hold time: 30s — no 45s, no 60s
- No redundant stretches: exercises that hit the same muscle group,
  include only once
 - Piriformis stretch = Figure-4 stretch (identical) — only one
   variant per session
 - 90/90 hip stretch ≠ Piriformis (different orientation, both ok in
   one session)
- Cool-down: max 3–4 stretches, each 30s/side

**Research anchor:** [Pre-exercise stretching — hold times & performance effects](../research/pre-exercise-stretching.md)

---

## Scientific sources (consolidated)

### Polarized / pyramidal distribution
- Seiler, S. (2010). "What is best practice for training intensity and
  duration distribution in endurance athletes?" *Int J Sports Physiol
  Perform*, 5(3), 276–291.
- Stöggl, T., & Sperlich, B. (2014). "Polarized training has greater
  impact on key endurance variables than threshold, high intensity, or
  high volume training." *Front Physiol*, 5, 33.
- Stöggl, T., & Sperlich, B. (2015). "The training intensity
  distribution among well-trained and elite endurance athletes."
  *Front Physiol*, 6, 295.
- Treff, G. et al. (2019). "The polarization-index: A simple calculation
  to distinguish polarized from non-polarized training intensity
  distributions." *Eur J Sport Sci*, 19(3), 380–384.
- Casado, A. et al. (2022). "World-class long-distance running
  performances are best predicted by volume of easy runs and deliberate
  practice of short-interval and tempo runs." *J Strength Cond Res*,
  36(8), 2272–2278.

### Fatigue / freshness / HRV monitoring
- Coggan, A. & Allen, H. (2019). *Training and Racing with a Power
  Meter* (3rd ed.). VeloPress. — Performance Manager Chart,
  CTL / ATL / TSB framework.
- Bourdon, P. C. et al. (2017). "Monitoring athlete training loads:
  Consensus statement." *Int J Sports Physiol Perform*, 12(Suppl 2),
  S2-161–S2-170.
- Bellenger, C. R. et al. (2016). "Monitoring athletic training status
  through autonomic heart rate regulation: A systematic review and
  meta-analysis." *Sports Med*, 46(10), 1461–1486.
- Lamberts, R. P. et al. (2010). "Heart rate recovery as a guide to
  monitor fatigue and predict changes in performance parameters."
  *Scand J Med Sci Sports*, 20(3), 449–457.
- Maunder, E. et al. (2021). "Cardiovascular drift in endurance
  exercise." *Sports Med*, 51(11), 2401–2421.

### DFA-α1 / VT thresholds from HRV
- Rogers, B. et al. (2021). "A new detection method defining the
  aerobic threshold for endurance exercise and training prescription
  based on fractal correlation properties of heart rate variability."
  *Front Physiol*, 11, 596567.
- Doerr, R. et al. (2021). "Validation of DFA-α1 thresholds for
  endurance exercise zone identification." *Int J Sports Med*, 42(13),
  1158–1166.

### Intervals / short-effort prescription
- Billat, V. L. (1999). "Interval training for performance: A scientific
  and empirical practice." *Sports Med*, 27(6), 373–386.
- Rønnestad, B. R. & Hansen, J. (2015). "Effects of 12 weeks of short
  versus long intervals on performance and physiological adaptations in
  highly trained cyclists." *Scand J Med Sci Sports*, 25(2), 143–151.
- Helgerud, J. et al. (2007). "Aerobic high-intensity intervals improve
  VO2max more than moderate training." *Med Sci Sports Exerc*, 39(4),
  665–671.

### Plyometric progression
- Markovic, G. & Mikulic, P. (2010). "Neuro-musculoskeletal and
  performance adaptations to lower-extremity plyometric training."
  *Sports Med*, 40(10), 859–895.

### Strides / running economy
- Daniels, J. (2013). *Daniels' Running Formula* (3rd ed.). Human
  Kinetics. — Strides as neuromuscular priming without fatigue cost.
- Magness, S. (2014). *The Science of Running.* Origin Press. — Stride
  prescription for trained runners.

### Cadence / gait retraining
- Heiderscheit, B. C. et al. (2011). "Effects of step rate manipulation
  on joint mechanics during running." *Med Sci Sports Exerc*, 43(2),
  296–302.
