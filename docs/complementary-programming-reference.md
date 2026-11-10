# Complementary programming reference (strength / plyo / core / balance)

Lookup detail for `agents/specialist-complementary.md`. The agent prompt keeps
the judgment rules short; this file carries the tables, exercise lists and
worked derivations behind them. Read the section the prompt points to when
the situation applies — not on every call.

## Contaminated slots

A slot is contaminated when another block in the same session has already
loaded the same chain, so the reported RPE describes the accumulated state,
not the exercise's own demand.

- Do not read the RPE as a progression trigger in either direction; carry the
  documented anchor forward and say so, so the post-session update does not
  overwrite the anchor with a contaminated value. A *passed* gate still counts
  (contamination inflates the number, so passing under it is a conservative
  lower bound); a *failed* gate does not.
- Terminate the set by a form criterion, not by the RPE ceiling: a fatigued
  stabilising chain degrades the movement while the rating stays plausible.
  Name the observable failure signature in the description (one-arm loaded
  carry: visible trunk lean, pelvic drop on the free side, rotation about the
  long axis, re-gripping) and make it the hard end of the set.
- RPE is still collected; it just does not move the plan that day.

Evidence and the ordering rule that avoids the situation:
[side-plank-prefatigue-vs-loaded-carry-same-day.md](../research/side-plank-prefatigue-vs-loaded-carry-same-day.md).

## Plyometric ladder and tissue-sparing selection

Levels (Markovic & Mikulic, 2010):

| Level | Pattern | Examples | Contacts / session |
|---|---|---|---|
| 1 basics | bilateral | box jumps, squat jumps, broad jumps | 40–60 |
| 2 intermediate | unilateral | single-leg hops, split-squat jumps | 30–40 |
| 3 expert | reactive | drop / depth jumps, bounding | 20–30 |

Advance a rung only on quality, never on session count: quiet and symmetric
landings, short ground-contact time (a fast-SSC drill that drifts long is
fatigue, not reactive stimulus), a symptom-free DOMS window, and — before any
unilateral rung — a symptom-free single-leg hop test.

Selection under an active lower-limb restriction follows the SSC axis:
concentric-dominant slow-SSC work (squat jumps, box jumps with step-down,
broad jumps) loads mainly quads and glutes; fast-SSC work (pogo, bounding,
depth / drop jumps) puts peak load on the lower-leg tendon and is
contraindicated under a tendon freeze. Minimum 48 h between plyo sessions.

Anchors: [plyometric-exercise-catalog-and-progression.md](../research/plyometric-exercise-catalog-and-progression.md),
[plyometric-progression-levels.md](../research/plyometric-progression-levels.md),
[plyometrics-frequency-recovery.md](../research/plyometrics-frequency-recovery.md).

## Hip-hinge choice in the 48 h before a long endurance session

| Class | Examples | Floor before the long session |
|---|---|---|
| Ballistic hinge | two-handed kettlebell swing | ~48 h, at an established load |
| Slow eccentric at long muscle length | RDL, Nordic curl, heavy split squat | ≥ 72 h |
| Concentric-dominant, short muscle length, bodyweight | single-leg hip thrust, glute bridge, short top hold | ≥ 24 h |

- A first exposure in the third class is not a load jump: cap it at 6–10
  reps, ~3 sets on the target side (+1 set on the weaker side when the signal
  is one-sided), RPE ≤ 6–7, no slow eccentric, progress via volume; the first
  loaded variant waits for 2–3 clean bodyweight sessions. A tempo eccentric
  (e.g. 3 s step-down) moves the exercise into the ≥ 72 h class.
- Not acceptable in the 48 h slot: a load jump (novelty breaks the
  repeated-bout protection — defer the step to a session ≥ 72 h out, the
  target anchor stands); ballistic hinge plus slow eccentric in one session;
  treating the substitution as permanent — a ballistic hinge trains no
  fascicle length, so a slow-eccentric exercise that carries a structural goal
  is re-placed at ≥ 72 h, and `focus` names where it returns.
- When the long session itself carries an open tissue-tolerance question,
  sequence it first and put the strength session after it.

Anchors: [ballistic-hip-hinge-vs-eccentric-rdl-before-longrun.md](../research/ballistic-hip-hinge-vs-eccentric-rdl-before-longrun.md),
[doms-peak-timing.md](../research/doms-peak-timing.md),
[concentric-glute-first-exposure-before-longrun.md](../research/concentric-glute-first-exposure-before-longrun.md).

## Heavy eccentrics before a quality run (PAP rule)

Heavy eccentric strength (loaded slow-tempo raises, loaded tempo RDL) does
not go before a threshold / VO2max session, earlier the same day or the day
before: it is tendon loading that dampens running performance for up to
24 h, not post-activation potentiation. PAP-eligible primers are short and
explosive: pogo hops (not under an active lower-leg tendon restriction —
use lateral bounds or strides then), lateral bounds, strides, skips. When in
doubt, omit the heavy eccentric. Source: `config/training_paradigms.md`;
anchor [eccentric-calf-pap-inhibition.md](../research/eccentric-calf-pap-inhibition.md).

## Target RPE — where it is required and where it is not

Required (`rpe_target` field plus inline `RPE X` / `RPE X-Y`):

- Every weighted exercise (`weight_kg` set) — squat and hinge variants,
  step-up, lunge, presses, curls, weighted dips / pull-ups. A load cap does
  not remove the requirement: the cap fixes the load, the RPE says whether the
  cap still fits.
- Bodyweight exercises at near-max recruitment — pull-ups, dips, loaded
  push-up variants, box jumps (pacing of explosiveness).
- Plyometrics with explicit volume — pogo hops, lateral bounds, depth jumps
  (effort cap and tendon-load tolerance).

Not used:

- Unloaded stability / endurance isometrics — side plank, bird dog, curl-up,
  dead bug, plank: progression is form, symptom signal and hold time.
- Balance / proprioception — the S1–S5 stability score replaces RPE.
- Mobility / activation drills — cat-cow, hip circles, wand slides.
- Light band physio — an RPE may be given as an upper cap ("RPE 4-5") but does
  not drive progression.

## Duration estimate for bilateral and isometric blocks

Compute bottom-up per exercise, never trust a directive's `duration_min`:

| Exercise type | Work per set | Multiplier |
|---|---|---|
| Isometric hold (side plank, bird-dog hold, plank, L-sit) | `hold_s` | × 2 when `per_side` |
| Reps with explicit tempo (3-0-3, 8 s holds) | `reps × rep_seconds` | × 2 when `per_side` |
| Reps without tempo | `reps × 3 s` | × 2 when `per_side` |
| Carry / hold (suitcase, farmer's, towel) | `hold_s` | × 2 when `per_side` |

Rest: 30 s between sets by default, 60–90 s between heavier isometric
exercises, plus ~20 s per set for a side switch in side-plank positions.
Rule of thumb: four bilateral hold exercises at 3 sets each (35 s holds,
8 reps/side, 6 reps/direction at 3-0-3, 10 reps/side with 8 s holds) land
near 29 min, not the 8 min a directive may state. Either override
`duration_min` with the bottom-up figure plus a one-line `duration_note`, or
push back to the planner when the gap exceeds factor 1.5. Mechanical
backstop: `validate_plan.py::check_duration_plausibility` (R018).

## Film tip — when to set one

Context: `planningConstraints` carries the film-tip status from
`exercise_log.md` (`⛔ Blocked` = video too recent, `📽 Candidates` = should be
filmed if it appears today; an exercise outside the log was never filmed).

A. Always fire: first appearance of the exercise in the type history; last
   RPE ≥ 8 and today the same load / reps (technique under fatigue); the
   athlete expressed technique doubt in history or feedback.

B. Fire when not blocked: the exercise is a `📽 Candidate`; the exercise was
   never filmed and has high technique risk (RDL, Bulgarian split squat,
   single-leg RDL, single-leg hop, box jump, jumping lunges — not simple
   isolation work such as curls); today's progression step changes the
   mechanics (bilateral → single-leg, ground → elevated).

C. Break a block (video < 7 days old): last RPE clearly outside expectation
   (planned 6, reported 9+, or 2 on a heavy exercise); technique doubt
   expressed after the last video.

Several candidates → the most technique-heavy / risk-relevant one; always one
film tip per session. Setup (claim → class → scale → camera, direction table):
[film-tip-setup.md](film-tip-setup.md).

## Physio prescriptions with several layers

When `athlete_static.md` describes a prescription as parallel layers with
different cadences (an atomic block on a shared cadence plus daily or
own-cadence exercises on top):

1. **An atomic block is atomic.** Its cadence check uses the oldest last-seen
   date among all its exercises; dropping a subset is forbidden. When a main
   block today would duplicate an exercise of the atomic block, the physio
   block stays and the main block adapts.
2. **A new prescription adds a layer** unless the athlete explicitly confirms
   a replacement. Read the prescription's as-of date and all layers together;
   "parallel to …" wording is binding.
3. **Each layer keeps its own cadence.** Daily layers run every day, including
   atomic-block days; own-cadence layers follow their own start anchor. Never
   collapse a layer into another layer's cadence.
4. **Verify last-seen per exercise** from `exercises_seen` in the type
   history, not from the session name: a session titled "… + Physio" that
   carried only a daily drill does not refresh the atomic block's cadence.

Cadence specifiers ("every other day", "every N days", in the athlete's
configured language) with a start anchor: compute the next on-cadence day from
the anchor; if today is off-cadence, leave the exercise out. Post-execution
cadence wins over the calendar anchor (last execution + interval > today →
still skip). A one-off off-cadence request from the athlete does not become
the new rule.

## Return after an acute non-specific back episode

When an athlete with an existing isometric trunk routine returns from an
acute non-specific back episode, do not answer with more isometric volume —
the routine builds endurance capacity, the episode exposed a timing deficit.
Once the acute phase has settled and the pain-monitoring gate allows load:

1. Reactive / unanticipated trunk tasks, unpredictable in timing and direction
   (what is trainable is pre-activation, not raw reflex latency — say so).
2. Hip-hinge practice in varied contexts — objects, speeds, cognitive
   distraction — so the pattern survives without conscious attention.
3. Lever-arm awareness as an explicit cue: load distance from the body
   dominates over back angle.

The existing isometric block stays at its anchors. Evidence and limits:
[recurrent-lbp-prevention-beyond-core-and-technique.md](../research/recurrent-lbp-prevention-beyond-core-and-technique.md).

## Half-kneeling hip-flexor positions — the rear leg is a dose variable

The rear leg's frontal-plane position decides which structure is loaded. Rear
leg in the sagittal plane (knee under the hip, no abduction, no internal
rotation): little stretch load reaches the proximal adductor group. Rear leg
abducted or internally rotated: the same position becomes a genuine adductor
stretch (shear modulus rises severalfold at 40° abduction). A glute squeeze
added to the position recruits adductor magnus as an extension synergist — a
different origin from the adductor longus enthesis; the evidence ranks the
two muscles, it does not show absence in either. Measured on muscle tissue,
not on the enthesis:
[groin-region-differential-and-half-kneeling-hip-flexor-load.md](../research/groin-region-differential-and-half-kneeling-hip-flexor-load.md).
