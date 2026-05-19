# Shoulder-rehab exercise frequency — daily vs. alternate-day vs. 3×/week

**Created:** 2026-05-19

---

## TL;DR

1. **Frequency for shoulder rehab is NOT a single number — it
   depends on the stress class of the exercise.** Mobility /
   light cuff-activation tolerates (and benefits from) **5–7 ×/week**
   because the load is low and motor learning gains accumulate.
   Stabi-strengthening with bands (cuff + scapula loading via
   resistance) belongs at **3 ×/week on non-consecutive days**
   because tissue adaptation needs ~48 h recovery between loading
   cycles. Combined ER + mobility patterns (W-raises, 90/90 rotations)
   land in between at **3–5 ×/week**.
2. **Concrete AAOS Rotator Cuff Conditioning protocol:** sleeper
   stretch and similar passive mobility → daily; pendulum / crossover
   stretch → 5–6 ×/week; trapezius strengthening + combined ER/IR →
   3–5 ×/week; band rows + bent-over horizontal abduction + scapular
   work → 3 ×/week.
3. **Practical implication for a coach system:** when a physio
   appointment adds new exercises, classify each by its stress class
   (mobility / combined / strengthening) and dose it accordingly —
   not a uniform "daily" or "every 2 days". This avoids both
   under-dosing the cuff activators and over-loading the
   strengthening pattern.
4. **Athletes with established daily shoulder routines:** keep the
   light-load mobility / activation exercises daily as the baseline,
   then add the strengthening exercises on M-W-F (or T-Th-Sa) as a
   3 ×/week layer on top. This produces ~5 min daily + ~3-4 min add
   on three days — total weekly time matches a single-block-per-day
   approach but respects the differential-frequency logic.

---

## Question / Trigger

A real-application pattern: a physio appointment adds several new
shoulder exercises (e.g. a combined ER/IR raise, a bow-and-arrow
rotation, a wall-slide band drill) to an existing daily cuff
activation exercise. The natural coach response is to propose a
uniform alternate-day rotation pool (N exercises/day from an M-pool,
each exercise hitting ~3-4 ×/week). That schema is pragmatic and
evenly distributed but does NOT match the AAOS / systematic-review
recommendation, which differentiates frequency by exercise stress
class.

Three concrete sub-questions:

1. What does the literature say about *uniform* high-frequency vs.
   *differentiated* frequency in cuff / scapula rehab?
2. Which exercise classes tolerate daily loading and which need
   spacing?
3. How does the recommendation change with rehab phase (acute /
   sub-acute / maintenance)?

---

## Findings

### 1. Frequency by exercise class — AAOS Rotator Cuff & Shoulder Conditioning

The official AAOS protocol differentiates four frequency tiers in a
single conditioning program:

| Frequency | Exercise class | Examples |
|-----------|----------------|----------|
| **Daily** (7 ×/week) | Passive stretching / mobility | Sleeper stretch (4 reps, 3 × per day) |
| **5–6 ×/week** | Initial mobility / pre-strengthening | Pendulum, crossover stretch, passive rotation |
| **3–5 ×/week** | Combined ER/IR + light scapular | Trapezius strengthening, combined rotation with light band |
| **3 ×/week, non-consecutive** | Band-resistance strengthening | Standing rows, ER/IR with stronger band, elbow flex/ext, scapular work, bent-over horizontal abduction |

Maintenance after the 4–6-week conditioning phase: 2–3 ×/week is
sufficient to retain strength + ROM.

The differentiation is explicitly load-and-tissue-based:
strengthening with band resistance is the only tier that needs
48-h recovery windows because that's where actual mechanical
adaptation happens. Stretching/mobility tiers can run daily because
the load doesn't trigger a recovery requirement.

**Source:** [AAOS — Rotator Cuff & Shoulder Conditioning Program](https://orthoinfo.aaos.org/en/recovery/rotator-cuff-and-shoulder-conditioning-program/)

### 2. Systematic-review evidence — scapular therapeutic exercises

Bury et al. 2024 / Stuart et al. (Effectiveness of specific scapular
therapeutic exercises in patients with shoulder pain — systematic
review with meta-analysis):

> "Scapular stabilization exercises performed 7 ×/week (84 sessions
> over 12 weeks) were more effective than interventions based on
> other exercises, indicating that daily exercise frequency may
> offer advantages for scapular kinematics in shoulder impingement
> syndrome."

But the same review notes a wider range of effective protocols from
**alternate-day** training (3–4 ×/week) up to daily, with the optimal
frequency depending on:

- Individual pain level
- Rehab phase
- Whether the protocol is a pure motor-learning / kinematics
  intervention (high frequency benefits) or a mechanical loading
  intervention (48-h recovery benefits)

**Take-away:** 3-4 ×/week is the conservative default for scapular
strengthening; daily is justified when the protocol is dominated by
motor-learning / kinematics goals OR when the load per session is
deliberately kept low.

**Source:** [Specific scapular therapeutic exercises systematic review (PMC11065746)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11065746/)

### 3. Co-creation inventory — physiotherapist consensus

Survey of physiotherapists working with rotator-cuff-related shoulder
pain (Naunton et al. 2022) — they categorise exercises into
"activation" (high frequency, low load), "stabilisation" (medium
frequency, medium load) and "strengthening" (lower frequency, higher
load), and dose accordingly. The exact frequency split varies but the
direction is consistent: load goes up → frequency goes down.

**Source:** [Co-creation exercise inventory scapular stabilization (PMC9003989)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9003989/)

### 4. UCSF Sports Medicine Rotator Cuff protocol

The UCSF rehab protocol structures the day as "daily mobility + 3 ×/week
strengthening" — the strengthening sessions are M-W-F or T-Th-Sa with
rest day on the off-day. Same logic as AAOS.

**Source:** [UCSF Rotator Cuff Protocol](https://sportsrehab.ucsf.edu/sites/g/files/tkssra10961/files/Rotator%20Cuff%20Injuries%20Protocol.pdf)

### 5. Rehab-phase scaling

Acute / pain-active phase (week 1–2 after diagnosis or flare):
- Activation work can run 2–3 × per day (very low load, motor cuing
  focus)
- Strengthening typically deferred

Sub-acute / mobility-build phase (week 2–6):
- Mobility daily, activation daily, strengthening introduced at
  3 ×/week

Maintenance phase (after week 6):
- Mobility 5–7 ×/week, strengthening 2–3 ×/week
- Drop activation to 3–4 ×/week if pain-free

A typical real-application setup will mix phases: new exercises sit
in the **sub-acute / mobility-build phase**, while a long-standing
daily cuff-activation exercise (e.g. External Rotation Band that has
been running daily for weeks without symptom escalation) is already
in the **maintenance phase**. Each exercise needs its own
phase-appropriate frequency, not a global block-level frequency.

---

## Application in framework

### What is changed / refined

1. **Wrapper `config/athlete_static.md` (athlete-specific):**
   Shoulder-rehab block pools are restructured from a single daily
   exercise + provisional alternate-day rotation pool into the
   AAOS-differentiated schema:
   - **Daily (7 ×/week):** light Activation / Mobility class
     exercises (e.g. cuff External Rotation Band + Wall Slides with
     band)
   - **M / W / F add (3 ×/week):** combined ER + shoulder mobility
     exercises (e.g. a W-Raise variation)
   - **Tue / Thu / Sat add (3 ×/week):** cuff + scap strengthening
     with band (e.g. a 90/90 Bow & Arrow variation)
   - **Sunday:** Daily only (active recovery)

   Result: each exercise lands in its AAOS-recommended frequency
   tier.

2. **`framework/agents/planner.md` / `specialist-complementary.md`:**
   New head-coach rule when adding NEW physio exercises to an
   existing rehab block (atomic or rotation-based): classify the
   exercise by stress type (mobility / activation / combined /
   strengthening) and dose accordingly, do NOT default to "same
   frequency as existing block". The classification questions:

   | Question | Implies frequency tier |
   |---------|------------------------|
   | Is the load primarily bodyweight / very light band? | Daily-tolerable (mobility / activation) |
   | Does the exercise combine ER/IR with another movement? | 3–5 ×/week (combined) |
   | Is the primary stress mechanical band resistance through cuff/scap loading? | 3 ×/week non-consecutive (strengthening) |

   This rule is added to `specialist-complementary.md` as part of the
   physio-block handling logic.

### What stays unchanged

- Atomic physio blocks (a multi-exercise routine prescribed by the
  practice as a coherent unit, fired every N days) keep their atomic
  structure — the differentiated frequency analysis does not apply
  inside an atomic prescription. New exercises from later
  appointments go into a separate pool unless the practice
  explicitly says "add this to the atomic block".
- Atomic LBP-stabilisation chains stay atomic — they are designed
  as a motor-learning unit, all exercises fire together on the
  prescribed cadence.

---

## Open questions / Caveats

1. **Athlete-feedback loop:** the AAOS schema is an evidence-based
   default. Real-world fine-tuning needs 2–3 sessions of feedback
   per new exercise — reps + RPE + perceived load. If RPE on a
   combined-tier exercise consistently lands ≤ 4
   (under-stimulating), it shifts up to the 3–5 ×/week tier (e.g.
   Mo/Mi/Fr/Sa = 4 ×/week instead of 3). If RPE on a strengthening
   exercise consistently lands ≥ 7 (close to a strengthening
   threshold), keep at 3 ×/week and don't push higher.
2. **Acute flare-up handling:** if pain or shoulder warmth reappears
   in the rotation, drop the strengthening tier first, keep only
   the mobility/activation daily layer until the flare clears. Then
   re-introduce 1 strengthening exercise per session, alternating,
   before going back to the full schema.
3. **Atomic-block + pool interaction:** an atomic shoulder block
   and a daily pool can run in parallel. On days when both are due,
   the cumulative shoulder volume is higher — that's expected and
   intended (the atomic block is the rehab anchor, the pool is the
   daily complement). If total shoulder volume becomes excessive on
   a combined day, drop the pool's strengthening add on that day
   (push it to the next day in its tier).
4. **Long-term progression vector:** the AAOS conditioning programme
   is designed for 4–6 weeks then maintenance at 2–3 ×/week. An
   ongoing low-grade restriction (not a discrete injury rehab)
   argues for keeping the daily activation + 3 ×/week strengthening
   as a permanent baseline rather than ramping down — the
   "maintenance" reduction applies cleanly only after a discrete
   rehab episode resolves.

---

## Primary sources

| Author / publication | Title | Link | Key quote |
|----------------------|-------|------|-----------|
| AAOS — OrthoInfo | Rotator Cuff & Shoulder Conditioning Program | [orthoinfo.aaos.org](https://orthoinfo.aaos.org/en/recovery/rotator-cuff-and-shoulder-conditioning-program/) | "Sleeper stretch 4 reps 3× a day [daily]; pendulum/crossover stretches [5-6 ×/week]; combined IR/ER + trapezius [3-5 ×/week]; band rows + scapular strengthening [3 ×/week, non-consecutive]" |
| Stuart et al. 2024 (sys-review, meta-analysis) | Effectiveness of specific scapular therapeutic exercises in patients with shoulder pain | [PMC11065746](https://pmc.ncbi.nlm.nih.gov/articles/PMC11065746/) | "scapular stabilization 7×/week (84 sessions/12 weeks) more effective than other interventions … optimal frequency depends on rehab phase and load intensity" |
| Naunton et al. 2022 (Co-creation survey) | Co-creation of an exercise inventory to improve scapular stabilization and control among individuals with rotator cuff-related shoulder pain | [PMC9003989](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9003989/) | "activation / stabilisation / strengthening categorisation — load up = frequency down" |
| UCSF Sports Medicine | Rotator Cuff Injuries Protocol | [sportsrehab.ucsf.edu](https://sportsrehab.ucsf.edu/sites/g/files/tkssra10961/files/Rotator%20Cuff%20Injuries%20Protocol.pdf) | "daily mobility + 3×/week strengthening pattern" |
