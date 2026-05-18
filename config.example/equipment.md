# Available equipment — Alex Demo

> Demo defaults. Replace with your own `config/equipment.md` listing actual
> shoes, weights, devices.

## Running shoes
*(YAML-like list parsed by `shoe_advisor.load_shoe_profiles()`. Replace
`strava_id` values with your real Strava gear IDs when you sync. Demo IDs
below let the framework run end-to-end without a Strava connection.)*

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
