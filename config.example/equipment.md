# Available equipment — Alex Demo

> Demo defaults. Replace with your own `config/equipment.md` listing actual
> shoes, weights, devices.

## Running shoes
*(YAML-like list parsed by `shoe_advisor.load_shoe_profiles()`. Replace
`icu_gear_id` values with your real intervals.icu gear IDs. Demo IDs below
let the framework run end-to-end without a gear connection.)*

**Field reference.** Each profile starts with `- icu_gear_id: <id>` (the intervals.icu gear id;
`gear_id:` is accepted too), followed by indented `key: value` lines. HTML
comments are stripped before parsing.

| Field | Values | Effect |
|---|---|---|
| `name` | free text | Display name. |
| `type` | `tempo` · `easy` · `long` · `trail` · `recovery` | Shoe category. The fleet check warns when one of these five has no active shoe, or only one that is past 80 % of its `threshold_km`. |
| `role` | `daily` (default) · `race` | `race` locks the shoe to RACE sessions and to the `race_prep_days` before a race — never on a treadmill. |
| `primary_race` | `true` | Marks the current main race shoe (set it on one shoe only): strong bonus for matching sessions inside the prep window. |
| `terrain` | `asphalt` (default) · `trail` · `mixed` · `track` | Trail sessions need `trail` or `mixed`; asphalt and track sessions exclude `trail`. |
| `race_prep_days` | integer, default 7 | Days before a race from which a `role: race` shoe is released. |
| `active` | `false` | Keeps a profile on file but out of the rotation. |
| `cushion` | `low` · `medium` · `max` | Descriptive only; no code reads it. |

**Replacement mileage by category** (`threshold_km`, default 800; manufacturer
guidance and practitioner consensus, not a per-shoe measurement): carbon-plated
race shoe 400–500 km (plate and foam lose energy return first) · carbon-plated
trainer 600–700 km · lightweight tempo shoe without a plate 600–700 km ·
medium-cushion daily trainer 700–800 km · max-cushion daily trainer 900–1000 km
(thicker foam stacks degrade more slowly) · trail shoe 700–800 km (outsole wear
adds to foam fatigue; earlier on rough terrain).

Optional per-shoe fields that steer the recommendation:

| Field | Effect |
|---|---|
| `pace_range_min_km: [min, max]` | Hard filter. The shoe is dropped unless its pace range overlaps the session's pace bucket by at least half. |
| `required_workout_type: RECOVERY` | Hard filter. The shoe is offered **only** for that session type. |
| `excluded_workout_types: [long, race]` | Hard filter, the inverse of the above — the shoe is fine in general but unsuited to these sessions (e.g. a medium-cushion daily on a long run). Matched against tags, intensity and workout type alike. |
| `recommended_tags: [easy, recovery]` | Soft bonus only. Nudges a matching shoe ahead of an equally-rested one; deliberately too small to override the rotation bonus. |
| `threshold_km` | Replacement mileage. Drives the wear penalty and the "renew soon" warning. |

Leave them unset to keep a shoe eligible everywhere — the defaults are
permissive on purpose.

- icu_gear_id: b1234567
  name: "Demo Daily Trainer"
  role: daily
  type: easy
  terrain: asphalt
  threshold_km: 800

- icu_gear_id: b2345678
  name: "Demo Tempo Shoe"
  role: tempo
  type: tempo
  terrain: asphalt
  threshold_km: 600

- icu_gear_id: b3456789
  name: "Demo Race Carbon"
  role: race
  type: race
  terrain: asphalt
  threshold_km: 250
  race_prep_days: 14

- icu_gear_id: b4567890
  name: "Demo Trail Shoe"
  role: trail
  type: trail
  terrain: trail
  threshold_km: 600

## Strength equipment
- Kettlebell set: 8 / 12 / 16 / 20 / 24 kg
- Dumbbells: adjustable, 2.5 – 20 kg per hand
- Pull-up bar (doorway)
- TRX suspension trainer
- Resistance bands: light / medium / heavy

## Cardio equipment
- Treadmill (optional)
- Indoor bike trainer (smart, optional)

## Devices
- GPS watch
- HR strap (chest)
- Power meter (bike, optional)

## Camera (optional, for form check)
- Phone camera tripod
- Drone (optional)
