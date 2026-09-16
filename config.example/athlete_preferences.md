# Athlete preferences — Alex Demo

> Demo defaults. Replace this file with your own `config/athlete_preferences.md`
> to override language, sport priorities, outdoor/indoor rules, etc.

## Language
- Coach response language: **en** (English)
- Override locally with `language: <code>` (e.g. `language: de`)

## Acceptance phrases
The Coach pushes a plan when the athlete confirms with one of these phrases:
- `ok`
- `yes`
- `good`
- `sounds good`
- `go`

## Sport priorities (in order)
1. Running — endurance, technique, race prep
2. Strength / complementary training
3. Mobility & balance

## Outdoor vs. indoor rules
- Default: prefer outdoor for runs unless weather is extreme or terrain
  unsafe.
- Indoor (treadmill / Zwift) appropriate when:
  - Wet+cold combined (rain + < 5 °C)
  - High wind > 40 km/h
  - Icy roads
  - Pollution alert
- Strength training: indoor unless the athlete specifies otherwise.

### Indoor running (treadmill) — dosing a belt session against an outdoor target

Device limits (top speed, incline range, adjustment lag, heat) are
athlete-specific and belong in the wrapper. What follows is generic.

**Grade: one correction axis, never two.** The widely repeated "always set
1 %" is weaker than its popularity suggests — it rests on a single
nine-runner study, and later repetitions disagree, one of them explicitly
rejecting a universal 1 %. The per-speed resolution of that original study
puts the threshold near **3.75 m/s (~13.5 km/h, ~4:27/km)**: below it, 0 %
already matched outdoor. **This number comes from a secondary transcription
of the study's table — the original is paywalled — so treat it as the best
available figure, not a verified one**, and keep that caveat attached
wherever it is applied.

| Target speed | Grade |
|---|---|
| ≤ ~13 km/h | 0 % |
| ~13–16 km/h | 0 % **or** 1 % — pick one axis (see below) |
| > ~16 km/h | 1 % |

**⛔ No double correction.** Running the belt *faster* than the outdoor
target and adding grade corrects the same missing air resistance twice, and
the session lands above its intended intensity. Either raise the belt speed
**or** set the grade. When the athlete has already chosen the faster belt
speed, the grade stays at 0 % — and that is a decision, not an absence of
one. Say so, or it reads as an oversight.

**"Energetically different" is not the same as "1 % fixes it."** Repetitions
of the original work show treadmill-specific extra cost that has nothing to
do with air resistance, so grade cannot be expected to close the whole gap.

**HR ceiling: raise it by ~5–8 bpm** for the same target pace, because there
is no cooling airflow. This figure is **practitioner consensus, not a
peer-reviewed point estimate** — label it that way when it is used. RPE also
sits roughly one CR10 point higher indoors. Neither is a drift finding; both
are the indoor signature. The cheapest lever against both is a fan running
from minute zero, not a slower belt.

**A belt session is not a pace anchor.** Belt calibration error (a
manufacturer-side convention of ±2–3 %, also not peer-reviewed), the thermal
HR premium, the RPE shift and the treadmill-specific energy cost stack in the
same displayed number. A treadmill session can still serve as an **RPE
reading at a controlled speed** — but compared against a treadmill baseline,
never against the outdoor one.

Derivation, sources and the evidence-vs-convention split:
`framework/research/treadmill-vs-outdoor-pace-hr-and-1-percent-grade.md`.

## Warm-up policy
- Default warm-up: 10 min easy with 3–4 short drills (A-skip, leg swings,
  ankle bounces) on running days.
- Strength days: 5–8 min mobility flow, then 1–2 ramp-up sets per exercise.
- Avoid duplicating drills across multiple workouts on the same day —
  consolidate into one warm-up at the day's hardest stimulus.

## Time windows
- Preferred morning window: before 09:00
- Preferred evening window: 17:00–20:00
- Avoid: 21:00+ (sleep impact)

## Communication style
- Direct, no fluff.
- Reasoning in 2–3 sentences max.
- Push back politely when the athlete asks for something inconsistent with
  the data (overreaching, ignoring HRV drop, etc.).
