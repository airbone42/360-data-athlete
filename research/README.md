# Sport-scientific research library

Persistent collection of research findings that ground decisions in the coach framework. Each document bundles **primary sources + derivation for our paradigms** on a concrete topic (protocol, exercise, scaling question, periodisation detail).

## Purpose

- **Mandatory before scaling / adjustment / new exercise:** Before a specialist or planner adjusts an existing stimulus up/down OR introduces a new exercise/format, the research stored here is read. If no entry exists yet → research first, persist it, then apply (see `framework/CLAUDE.md` → "Research-before-scaling-or-new-protocol").
- **Flag-driven entries:** When a coach agent hits a genuine evidence gap it emits a `🔬 RESEARCH-FLAG`; after athlete approval, `/research` launches the `research-analyst` subagent, which adds a new document here following the schema below (see `framework/CLAUDE.md` → "Agent-flagged uncertainty"). Documents must stay athlete-agnostic — see Sphere discipline at the bottom.
- **Rationale anchor:** When a coach uses a "because study X" line in athlete communication, the study must be findable here with full quote + bibliography. No vague "the literature says" statements without source.
- **Drift protection:** Paradigms in `config/training_paradigms.md` or `framework/config.example/training_paradigms.md` contain numbers/ranges (e.g. "30s @ 130-145% FTP"). These must stay consistent with the corresponding research document. When new research refutes an older statement, the paradigm entry is updated AND annotated with a reference to the research document.

## Format of a research document

Each document follows this schema:

```markdown
# <Topic>

## TL;DR
One to three lines — the operative statement the coach system applies.

## Question / Trigger
What did we want to know, and why (trigger, date, affected incident).

## Findings
The scientific answer to the question, evidence-based. Structured by
sub-questions where relevant.

## Primary sources
List with title, authors, year, journal/publisher, link, one key quote.

## Application in framework
Which paradigms / agent rules / configs change as a result?
Path references + date.

## Open questions / Caveats
What the research did NOT clarify — and what should be checked next.
```

## Index

| Date | Topic | File | Status |
|------|-------|------|--------|
| 2026-06-30 | Sand / beach running as a training stimulus — ~1.6× energy cost, lower GRF but higher calf/Achilles per-stride load, weak road-economy transfer, generic progression (firm wet → soft dry, shod → barefoot, camber discipline) | [sand-running.md](sand-running.md) | active |
| 2026-06-28 | Single-finger isolation vs. whole-hand grip training — Force-Deficit/Enslaving real, aber Multi-Finger bleibt Hauptvektor; Isolation nur Rehab / dokumentierte Asymmetrie / Mono-Spezifik | [single-finger-isolation-vs-whole-hand-grip.md](single-finger-isolation-vs-whole-hand-grip.md) | active |
| 2026-06-23 | Lumbar core stabilization (McGill Big 3) for mild non-specific LBP — neutral isometric endurance + hip-flexor mobility + glute activation; loaded lumbar flexion contraindicated while irritated | [lumbar-core-stabilization-mcgill-big3.md](lumbar-core-stabilization-mcgill-big3.md) | active |
| 2026-06-20 | HM race HR vs. training HR — pace-leads/HR-guardrail; duration-dependent HR ceiling; "chase race HR" anti-pattern | [hm-race-hr-and-training-hr.md](hm-race-hr-and-training-hr.md) | active |
| 2026-06-19 | Warm-up priming before VO2max / Threshold intervals — short heavy spikes accelerate VO2 on-kinetics in rep 1 | [warmup-priming-intervals.md](warmup-priming-intervals.md) | active |
| 2026-06-18 | HRV prediction vs readiness classification — is "predict next-day HRV from yesterday's load" the right model form? | [hrv-prediction-vs-readiness-modeling.md](hrv-prediction-vs-readiness-modeling.md) | active |
| 2026-06-03 | Race pacing and load metrics — why CTL/TSB are not a short-race pacing ceiling | [race-pacing-and-load-metrics.md](race-pacing-and-load-metrics.md) | active |
| 2026-05-19 | Hard-easy microcycle around Quality — day-before / day-of / day-after design | [hard-easy-microcycle-around-quality.md](hard-easy-microcycle-around-quality.md) | active |
| 2026-05-19 | Shoulder-rehab exercise frequency — differential dosing by stress class | [shoulder-rehab-frequency.md](shoulder-rehab-frequency.md) | active |
| 2026-05-19 | Passive vs. active dead hang — when is each indicated? | [passive-vs-active-hang.md](passive-vs-active-hang.md) | active |
| 2026-05-16 → 2026-06-19 | VO2max short intervals (30/15, 30/30) — intensity, volume, scaling + inter-set recovery duration (3–5 min band) | [vo2max-short-intervals.md](vo2max-short-intervals.md) | active |
| 2026-05-21 | VO2max long intervals (Norwegian 4×4 etc.) — intensity, volume, scaling | [vo2max-long-intervals.md](vo2max-long-intervals.md) | active |
| 2026-05-16 | Intervals.icu workout-builder syntax — step targets, repeats, cadence | [intervals-icu-workout-syntax.md](intervals-icu-workout-syntax.md) | active |
| 2026-05-16 | Hill repeats — gradient, duration, intensity, typology (run) | [hill-repeats.md](hill-repeats.md) | active |
| 2026-05-16 | HRV forecast model — load→HRV regression, methodology, verdict zones | [hrv-forecast-model.md](hrv-forecast-model.md) | superseded (→ [hrv-prediction-vs-readiness-modeling.md](hrv-prediction-vs-readiness-modeling.md)) |
| 2026-05-16 | HRV and RHR baseline methodology — window, statistics, trigger thresholds | [hrv-rhr-baseline-methodology.md](hrv-rhr-baseline-methodology.md) | active |
| 2026-05-16 | Recovery-week triggers — 3-gate logic against Issurin/Meeusen/Coggan standards | [recovery-week-triggers.md](recovery-week-triggers.md) | active |
| 2026-05-16 | Cross-sport HR differential — Run vs. Bike vs. Swim (HRmax + LTHR) | [cross-sport-hr-differential.md](cross-sport-hr-differential.md) | active |
| 2026-05-16 | Achilles tendinopathy rehab — phases, pain monitoring, return-to-sport | [achilles-rehab-phases.md](achilles-rehab-phases.md) | active |
| 2026-05-16 | MAP — Maximum Aerobic Power, ramp-test protocols, FTP relationship | [map-ftp-ramp-test.md](map-ftp-ramp-test.md) | active |
| 2026-05-16 | Polarized training distribution — Seiler 80/20 as evidence-based standard | [polarized-training-seiler.md](polarized-training-seiler.md) | active |
| 2026-05-16 | Pyramidal distribution — when instead of polarized | [pyramidal-distribution.md](pyramidal-distribution.md) | active |
| 2026-05-16 | Compliance and decoupling thresholds — reprogram trigger after quality | [compliance-decoupling-thresholds.md](compliance-decoupling-thresholds.md) | active |
| 2026-05-16 | Cross-training VO2max transfer — bike stimulus for run adaptation | [cross-training-vo2max-transfer.md](cross-training-vo2max-transfer.md) | active |
| 2026-05-16 | Plyometrics — frequency, 48h recovery, CNS adaptation | [plyometrics-frequency-recovery.md](plyometrics-frequency-recovery.md) | active |
| 2026-05-16 | Plyometric progression levels 1-3 — volume + bilateral→unilateral | [plyometric-progression-levels.md](plyometric-progression-levels.md) | active |
| 2026-05-16 | Eccentric calf loading before intervals — PAP inhibition, not facilitation | [eccentric-calf-pap-inhibition.md](eccentric-calf-pap-inhibition.md) | active |
| 2026-05-16 | Maximal-strength protocols — 4×4-6 @ 80-85% 1RM standard | [maximal-strength-protocols.md](maximal-strength-protocols.md) | active |
| 2026-05-16 | Hypertrophy rep range — Schoenfeld sweet spot + 15-rep validator | [hypertrophy-rep-ranges.md](hypertrophy-rep-ranges.md) | active |
| 2026-05-16 | Downhill running — eccentric damage, DOMS timeline, taper recommendation | [downhill-running-doms-taper.md](downhill-running-doms-taper.md) | active |
| 2026-05-16 | DFA-α1 — non-linear HRV index for threshold estimation | [dfa-alpha1-vt-estimation.md](dfa-alpha1-vt-estimation.md) | active |
| 2026-05-16 | Concurrent training interference — strength + endurance temporal order | [concurrent-training-interference.md](concurrent-training-interference.md) | active |
| 2026-05-16 | Strava GAP vs. Intervals.icu GAP vs. Minetti — algorithms, differences | [strava-vs-intervals-gap.md](strava-vs-intervals-gap.md) | active |
| 2026-05-16 → 2026-05-17 | Strides — neuromuscular priming, running economy, format parametrisation (Paavolainen 1999, stop conditions, 4-vs-6 dosing) | [strides-protocol.md](strides-protocol.md) | active |
| 2026-05-17 | Cardiac startup drift — minute-0–10 HR transient (onset overshoot + cardiac-output lag + strap dry-contact); 10-min exclusion convention | [cardiac-startup-drift.md](cardiac-startup-drift.md) | active |
| 2026-05-16 | DOMS — peak timing, recovery window, 3-day validator window | [doms-peak-timing.md](doms-peak-timing.md) | active |
| 2026-05-16 | Static stretching pre-exercise — dose-response, 30s sweet spot | [pre-exercise-stretching.md](pre-exercise-stretching.md) | active |
| 2026-05-16 | Running cadence — 180-spm myth, self-selected, +5% rehab | [running-cadence-myths.md](running-cadence-myths.md) | active |
| 2026-05-16 | Brick-running intensity — Z2 vs. Z1, cardiac drift | [brick-running-intensity.md](brick-running-intensity.md) | active |
| 2026-05-16 | Ninja set-volume tolerance — max. 3 sets, connective-tissue limit | [ninja-set-volume-tolerance.md](ninja-set-volume-tolerance.md) | active |
| 2026-05-16 | Grip-training progression — bilateral → unilateral → combined | [grip-training-progression.md](grip-training-progression.md) | active |
| 2026-05-16 | Hamstring pre-lift static stretch — 2×30s before RDL | [hamstring-pre-lift-stretch.md](hamstring-pre-lift-stretch.md) | active |
| 2026-05-16 | Masters-athlete protein requirements — daily dose, per-meal, timing | [masters-protein-requirements.md](masters-protein-requirements.md) | active |

## Sphere discipline

This directory is **framework-generic** — the research findings apply to every athlete who uses the framework. Athlete-specific application (which athlete runs which protocol when) belongs in `config/` (wrapper) or in the athlete's intervals.icu NOTEs, not here.

If a research finding requires athlete-individual adjustment (e.g. "athlete's FTP anchor"), the generic logic is stored here, the individual numbers live in `config/athlete_status.md`.
