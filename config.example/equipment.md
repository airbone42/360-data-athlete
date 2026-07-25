# Available equipment — Alex Demo

> Demo defaults. Replace with your own `config/equipment.md` listing actual
> shoes, weights, devices.

## Running shoes
*(YAML-like list parsed by `shoe_advisor.load_shoe_profiles()`. Replace
`strava_id` values with your real Strava gear IDs when you sync — or use
`icu_gear_id` when the gear lives natively in intervals.icu. Demo IDs below
let the framework run end-to-end without a gear connection.)*

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

- strava_id: g_demo_daily
  name: "Demo Daily Trainer"
  role: daily
  type: easy
  surface: asphalt
  threshold_km: 800

- strava_id: g_demo_tempo
  name: "Demo Tempo Shoe"
  role: tempo
  type: tempo
  surface: asphalt
  threshold_km: 600

- strava_id: g_demo_race
  name: "Demo Race Carbon"
  role: race
  type: race
  surface: asphalt
  threshold_km: 250
  race_prep_days: 14

- strava_id: g_demo_trail
  name: "Demo Trail Shoe"
  role: trail
  type: trail
  surface: trail
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
