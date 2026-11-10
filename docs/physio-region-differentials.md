# Physio consultant — region playbooks

Look-up material for `agents/physio-consultant.md`. Read the section that
matches the reported region **only when the report falls there**; the
consultant prompt itself stays region-neutral. Every section assumes the
red-flag sweep in the prompt came back clean.

## Tendon rehab — phase transition

On a request to advance a tendon-rehab phase (isometric → isotonic →
energy-storage / plyometric):

1. **Pain monitoring** against the protocol thresholds: pain during/after
   loading ≤ 5/10, settled by the following morning, no week-over-week rise
   in pain or stiffness. Any threshold violated → phase stays; name the
   criterion.
2. **Clearance before energy-storage / plyometric reintroduction:** several
   weeks (typically 6–8) of consistent heavy-slow-resistance / eccentric
   loading completed; pain-free single-leg loading of the affected structure
   at target volume; a single-leg hop test without provocation; thresholds
   met throughout the preceding week.
3. Phase model and transition criteria: the matching tendon-rehab document in
   `research/` (index `research/README.md`). Recommend updating the phase
   entry in `config/athlete_static.md` only after the checklist passes, and
   state which items could not be verified without hands-on testing.

## Lower-leg soreness after an unusual exposure

Trigger: shin / lower-leg soreness after an **unstructured exposure**
(unsupportive footwear, a first barefoot or minimalist session, a long walk
on hard ground, a downhill hike). Do not default to DOMS — three conditions
look alike at first report and diverge by weeks:

| Condition | Location | Timeline |
|---|---|---|
| Exposure DOMS | Anterolateral (dorsiflexors / evertors) | Peak 24–72 h, resolved by day 5–7 |
| Medial tibial stress syndrome | Posteromedial, distal medial tibial border | Weeks; graded return-to-run |
| Chronic exertional compartment syndrome | Anterior compartment, exertion-locked | Specialist work-up |

Bedside questions before any load recommendation:

1. **Palpation along the medial tibial border over ≥ 5 cm** reproduces the
   pain? Positive → MTSS pathway (weeks-scale, no tempo stimulus this week).
2. **Warm-up behaviour:** fades and stays away → fits DOMS; fades and
   returns, or appears after a reproducible number of minutes → raises CECS.
3. **Neurological signs** (numbness, tingling, foot drop, tense swollen
   compartment) → refer, do not dose.

All three negative and diffuse muscular soreness → exposure DOMS; release
cascade in the lower-leg DOMS / MTSS document in `research/` and
`docs/lower-leg-soreness-gate.md`.

Do not argue risk via a slowed protective reflex: the reflex is too slow to
prevent a sprain anyway; protection is feed-forward (pre-activation, foot
placement). Extra caution in the acute window is justified only for a
**recurrent** instability history, which loses its landing compensation
under fatigue.

## Medial groin / proximal thigh region

A report here is a **region**, not a diagnosis. Rank across the five Doha
categories (adductor-, iliopsoas-, inguinal-, pubic-, hip-joint-related) as a
distribution; more than one entity can coexist.

- Pain on stretch does not discriminate (the stretch test does not help
  classify). Palpation to the centimetre (adductor origin vs. symphysis vs.
  inguinal canal) and resisted testing do — offer palpation as the first
  self-test.
- A negative squeeze test is triage, not exclusion; the strongest negative
  evidence comes from acute-injury cohorts, not slow overuse presentations.
- Name the population transfer: most adductor evidence is from male
  multidirectional-sport athletes. In endurance runners iliopsoas-related
  ranks ahead, and obturator-nerve entrapment (exertional, starting at the
  adductor origin, radiating distally, with paraesthesia) is the usual
  "maybe not the adductor at all".
- Quote prognosis from the acute **or** the longstanding row, never a blend;
  a study's treatment period is not a return date.

Evidence and time constants: the groin-region differential document in
`research/`.

## Acute non-specific low-back episode in an athlete who already trains the core

When a trunk programme is already running and the lifting pattern is intact
(movement from hips and knees, torso upright), do not conclude "insufficient
core" or "poor technique". The failure mode is **timing, not capacity**:
isometric work builds endurance but does not close reflex / feed-forward
latencies in fast, unanticipated movements.

Not to be issued as prevention: pre-bracing before a lift (no preventive
evidence; fails in the unguarded moment), and posterior-chain stretching as
low-back prevention (very weak marker; the mechanism does not apply when the
movement comes from hips and knees).

Residual risk pool: movement speed and unanticipated load, lever arm (load
distance dominates back angle), rotation / asymmetry, preview time, load
changing mid-lift, fatigue with divided attention.

Acute dosing: `research/lumbar-core-stabilization-mcgill-big3.md`; rebuild
and recurrence: `research/recurrent-lbp-prevention-beyond-core-and-technique.md`.
The 4–8 weeks after an episode are the high-risk window for the next one —
route the prevention plan into it.
