# Endurance specialist — run prescription detail

Detail for `agents/specialist-endurance.md`. The agent keeps the rules it
needs to write a run (steering mode, step syntax, HR bands, strides format,
the compliance matrix); this file carries the derivations behind them. Read
the relevant section when a session hits one of these cases and the short
rule in the agent is not enough. Companion files: `docs/endurance-ride-rules.md`
(rides), `docs/lower-leg-soreness-gate.md`, `docs/plated-race-shoes.md`,
`docs/running-video-clips.md`.

## Heat

**Easy / Z2.** The HR ceiling stays where it is; the pace that ceiling buys is
slower. Expected magnitude for an unacclimatised athlete: ~0.3–0.5 % pace loss
per °C above a ~10–15 °C reference, scaled by humidity (no scaling below a
~15–18 °C dew point, ×1.3–1.8 above it) and by acclimatisation (×0.5–0.7 once
adapted, which takes 10–14 days). Dew point is the better reference than air
temperature. The figure is a magnitude, not a prediction. When a pace
corridor is stated at all, derive it from the cool-weather anchor times the
expected penalty; never quote the cool-weather pace and let the athlete chase
it against the HR cap.

**Recovery band.** Heat lifts the HR floor reached during a jog recovery just
as it lifts the working HR. A recovery band copied from cool conditions is
unreachable, and the analysis then reads every recovery as a compliance gap.
Move the band with the conditions. When the recovery genuinely has to land,
change its form (walk the first 20–30 s), not the number.

**Quality block in heat.** At threshold / race-pace intensity HR drifts
5–15 bpm upward for an unchanged pace. A cap that is right in the cool is hit
early, and an athlete who obeys it slows well below target, which the
analysis then reads as a capability drop that did not happen. Raising the cap
is the mirror error. Steer the block by breathing and RPE (race-pace breathing:
short phrases possible, full sentences not) and let HR mark only the upper
bound. Keep the pace corridor at the documented anchor and let the result land
at its slow end; the heat allowance belongs in the interpretation, not in the
target. In the notes, say what a cap hit means: at the cap with race-pace
breathing is the heat signature; at the cap with breathing past race pace is
genuinely too fast.

**Hydration (> ~60 min in heat).** The pre-load is the lever: 400–600 ml in
the two hours before the start buys more than any realistic drinking rate
during the session (gastric uptake caps at ~0.8–1.0 L/h, real-heat sweat rates
exceed it). With a measured sweat rate on file, size the deficit against a 2 %
body-mass threshold and say whether the planned carry suffices. Electrolyte
concentration follows the athlete's sweat-sodium measurement; a generic "one
tablet per bottle" is off by a factor of two or more at either end.

**Carbohydrate in a ≤ 75 min session** is gut training, not fuelling. In a
race-prep phase a small bolus taken while already running rehearses race
fuelling (the insulin response is blunted under exercise). Never introduce an
untried product in a measurement session; pair intake with fluid.

Sources: `research/heat-pace-penalty-at-fixed-hr.md`,
`research/fueling-hydration-heat-threshold-70min.md`.

## HM-pace and threshold HR ceilings

A maximal, well-paced HM averages ~93–95 % LTHR, settling at ~88–92 % in the
first third and drifting to ~95–98 % in the last (typical drift +4–6 bpm first
to second half; heat amplifies). The event average is therefore wrong as a
single training cap: too high for a short fresh rep (invites over-pacing,
the "chase race HR" anti-pattern), too low for a long continuous block. The
duration bands in the agent are built downward from race HR, because a short
fresh rep lacks the pre-start arousal and accumulated drift. That construction
only holds for a block run at race pace.

A threshold / T-pace rep is faster than HM pace, so its ceiling is LT2 itself
(~95–100 % LTHR), written as a ceiling on the series. At a correctly held LT2
pace HR drifts up across the series by roughly 4–6 bpm, so rep 1 cannot reach
the number the last rep reaches. Naming the series ceiling as rep 1's target
is achievable only by running above LT2, and the HR plateau in interval work
is largely blind to velocity, so the athlete gets no signal that it happened.
Both errors (ceiling too low, ceiling handed over as target) take an HR number
without the state it belongs to. Sources:
`research/hm-race-hr-and-training-hr.md`,
`research/threshold-interval-rest-duration-and-control-variable.md`.

## Threshold rest

Documented corridors for distance running: 1–2 min for Z3 reps of 3–12 min
(work:rest 5–3:1), 0:30–3 min for Z4 reps of 1–6 min (2–1.5:1), with a trend
toward longer relative rest as intensity rises. A 6-minute rep at LT2 sits on
the Z3/Z4 boundary, so 2:00 and 2:30 are both inside. At iso-effort, longer
rest produced a higher mean running velocity for the same time near VO2max.
Source: `research/threshold-interval-rest-duration-and-control-variable.md`.

## Strides

Strides at the end of a Z2 run activate fast-twitch fibres and preserve
running economy at negligible fatigue cost. Being short (≤ 25 s),
elastic-tendinous and recovery-buffered, they are PAP-compatible: they do not
count as plyometric load and are not blocked by a generic leg / plyo lock
after a hard session. A next-day quality session, including a cross-training
one, never justifies cutting the count; if same-system fatigue is a real
worry, the lever is the Z2 main-set duration.

Execution is judged by dynamics: on reps ≤ 30 s GPS pace lags by 10–40 s/km,
so a crisp stride can read 40–60 s/km too slow. A real stride shows a
step-length spike, a cadence lift and a GCT drop.

Naming: a ≤ 30 s block at 85–95 % effort is a neuromuscular primer. Race pace
is a sustained Z3/Z4 effort, far slower than a near-sprint, so a name like
"race-pace surges" on a 25 s block reads to the athlete as "go race-hard". HR
lag means 15–30 s cannot reach Z4; a genuine Z4 / race-pace stimulus needs
≥ 1–2 min reps with an HR target and belongs in the build, not in a taper or a
priming day.

Recovery-first ordering gives every stride, including the first after the main
set, a short jog lead-in and ends on the last stride; the cool-down absorbs the
trailing recovery. It applies only to end-of-run finishers, never to
activation strides before intervals.

Prior-day check: neuromuscular fatigue scales with intensity and eccentric
load, not duration. After a well-absorbed aerobic long run, judge reps 1–2
against the athlete's cadence / GCT / step-length baseline; autonomic markers
clear the session but are not a neuromuscular proxy.

Sources: `research/strides-protocol.md`,
`research/neuromuscular-readiness-day-after-aerobic-long-run.md`.

## Treadmill

- **Grade, one axis.** Default 0 % up to ~13 km/h, 1 % above ~16 km/h; in
  between pick one axis. Raising belt speed above the outdoor target and adding
  grade corrects the missing air resistance twice. The threshold figure rests
  on a secondary transcription of the only per-speed study; keep that caveat.
- **HR premium.** ~5–8 bpm higher for the same pace (no cooling airflow), RPE
  about one CR10 point higher. Practitioner consensus, not a measured value.
  The belt sets the pace, so breathing is the binding in-session criterion.
- **Not a pace anchor.** Belt calibration error, the thermal premium and
  treadmill-specific energy cost all land in the displayed pace.
- **Verified belt (`treadmill_dosing: pace`).** A `m:ss/km Pace` target makes
  the watch alarm against its own stride-derived treadmill pace, which is
  unreliable on a belt; an HR target would dose by HR. Hence belt speed in the
  cue and no watch target (R031). Dosing by the speed set on a verified belt
  is not the same as using the watch's treadmill pace as an anchor.
- **Structural load.** The only instrumented comparison (n = 3) found axial
  bone strains and strain rates 48–285 % higher overground. The belt is even
  like a road but loads less than any surface: right for aerobic volume at
  reduced structural cost, wrong for race-surface exposure before a
  firm-ground race.

Sources: `research/treadmill-vs-outdoor-pace-hr-and-1-percent-grade.md`,
`research/race-surface-exposure-in-easy-volume.md`.

## Warm-up priming

A pure easy warm-up does not prime VO2 kinetics: the first work reps run under
a slow primary-VO2 response and fall below the time-above-90 %-VO2max window,
which for short-rep formats is the whole stimulus. The recovery window between
the last spike and rep 1 is 3–10 min (shorter leaves residual fatigue, longer
lets the kinetic effect decay). Source: `research/warmup-priming-intervals.md`.

## Press-lap warm-up

A leading `~` in the duration (`Easy ~5m press lap`) breaks the parser: the
whole step is dropped from `workout_doc`. The `Xm` is only intervals.icu's
plan-view default; Garmin shows the cue text, hence the duration in the cue
(R023). Warm-up length positions the quality block in the day; overrunning it
pushes the main set into rising heat or falling light. Syntax traps in full:
`research/intervals-icu-workout-syntax.md`.

## Film-tip placement

For Run/Ride the athlete-facing description is the `intervals_icu` text
(`prepare_workout_events` writes it verbatim). `focus` never reaches the
watch or phone, so a film tip living only there is invisible when it has to be
executed. A gait variable measured on a bend, a camber or a gradient measures
the surface, not the runner. A cue-on clip answers "can the athlete do it on
command", which is almost never the open question; the habit question needs an
uncued clip. Posterior setup rules: `docs/running-video-clips.md`.
