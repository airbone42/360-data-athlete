# Lower-leg soreness gate

Detail for acute lower-leg soreness from an unstructured exposure (bad
footwear, a first barefoot session, a long walk on hard ground, a downhill
hike): `agents/specialist-endurance.md` ("Acute lower-leg DOMS — gate the
quality stimulus") and `agents/planner.md` ("Acute lower-leg soreness from an
unstructured exposure"). Both keep the gate itself: the time staging
(≤ 24 h / 24–72 h / > 72 h → physio), quality held rather than cancelled, and a
terrain default that is never a reinstated restriction. This file carries the
release criteria, the in-session gate, the structural consequences for the
prescription and the planner's terrain nuance. Read it before prescribing or
planning anything above easy on such a day.

## Specialist: gate the quality stimulus

When the briefing reports soreness in the **lower leg** (shin,
anterolateral compartment, peroneals, calf) from an **unstructured
exposure** in the last 72 h — unsupportive footwear, a first barefoot
or minimalist session, an unusually long walk on hard ground, a
downhill hike — that soreness gates the quality stimulus. This is a
different trigger from the eccentric-strength spacing rule: no training
session created it, so nothing in the type history flags it.

| Time since exposure | Default |
|---|---|
| ≤ 24 h | No tempo / threshold / race-pace. Easy Z2 reduced, or a non-impact modality. |
| 24–72 h | Quality **held** unless the release criteria below are met. |
| > 72 h with symptoms persisting | Not DOMS any more — the differential belongs to the physio consultant before any quality is scheduled. |

**Release criteria — all four, not a majority:**

1. Brisk walking is pain-free.
2. Palpation along the **medial** tibial border over ≥ 5 cm does not
   reproduce the pain (a positive finding is a weeks-scale problem, not
   a days-scale one).
3. The preceding easy run showed no exertion-locked pattern — no pain
   that appears reliably after a fixed number of minutes, no numbness.
4. An in-session gate is built into the prescription: an easy opening
   block long enough to read the symptom (≈ 15–20 min), with an
   explicit instruction to end the session there if the symptom grows
   or the gait changes.

**When the criteria are met, release the quality — do not shave the
target as a hedge.** The caution belongs in the HR cap, the abort
criteria and the surface choice, not in a quietly reduced pace corridor
or a shortened block: a lowered target silently re-anchors the
progression and reads as a capability drop in the record (see "No
silent conservatism" in CLAUDE.md).

**Two structural consequences for the prescription itself:**

- **Move the cool-down out of the risk window.** The end-of-session jog
  is where attention drops, cadence falls and ground contact
  lengthens. With lower-leg stabilisers already sore, prescribe the
  cool-down as **walking** rather than a slower jog — remove the phase
  rather than moderate it.
- **Prefer even, predictable ground for the session.** The gain is
  fewer perturbation events per unit time, not a better defence per
  event. Say so in those terms when justifying it, and — critically —
  label the surface choice as a **single-session, symptom-driven
  decision** whenever a standing terrain restriction was previously
  lifted by the athlete. A surface downgrade that reads as a reinstated
  restriction undermines a decision the athlete already made (see
  "Never silently drop or replace standing prescriptions").

**Research anchor:**
[peroneal-doms-inversion-defense-and-mtss-differential.md](../research/peroneal-doms-inversion-defense-and-mtss-differential.md).

## Planner: directive for the day

When `athleteFeedback` reports lower-leg soreness (shin, anterolateral
compartment, peroneals) from a **non-training** cause (bad footwear,
barefoot session, long walk, downhill hike):

- **24–72 h peak:** impact quality is gated, not cancelled. Name the
  gate in `coaching_notes` so the specialist builds an easy opening block
  + abort criteria.
- **Terrain default:** even surface is well-supported only with a
  **recurrent** lateral-instability history (those athletes lose
  protective landing compensation under fatigue). Without that history,
  state the surface choice as exposure reduction, not protection.
- **A terrain default is not a restriction.** If a standing terrain
  restriction was previously lifted, say in `coaching_notes` it is a
  single-session symptom-driven default — the lifted restriction stays
  lifted. Restrictions return only by explicit athlete confirmation.
- **>72 h:** route to physio consultant for differential before scheduling
  the next quality stimulus.
