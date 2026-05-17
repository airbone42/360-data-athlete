# Cardiac startup drift — early-exercise HR transients and the minute-0–10 exclusion window

## TL;DR

The first ~10 minutes of a run regularly show a transient HR rise (often
into Z3–Z4) at submaximal pace. The phenomenon has three additive
sources — autonomic onset overshoot, slow cardiac-output kinetics, and
(for chest-strap users) electrode dry-contact noise — and is a **known
measurement / onset-kinetics artefact**, not a training error or a
useful zone signal. For HR-based assessment (zone evaluation, efficiency
inference, decoupling), the canonical convention is to **exclude
minute 0–10** of the activity and analyse the steady-state window
onward.

## Question / Trigger

After a Z2 forest run the coach analysis flagged "Lap-4 HF-Spike
163 bpm in the warm-up" as a growth area, framed as "warm-up too fast,
cold start with hill". The athlete pushed back: this is a well-known
HR transient at exercise onset, exists across all of his sessions, and
must never appear as athlete error in coaching feedback. The fix
required a written reference so the rule is enforceable, not just an
inline note in agent contracts.

## Findings

### 1. Three superimposed mechanisms drive the early-exercise HR rise

The early-exercise HR pattern is the sum of three physiologically
distinct processes that often peak in the same minute-1–minute-5
window:

**(a) Autonomic onset overshoot / "central command" surge.** At
exercise onset, parasympathetic withdrawal happens within the first
1–3 heartbeats, followed by a sympathetic surge driven by central
command (cortex → cardiovascular control centre) and the muscle
metaboreflex. The result is an HR rise that **overshoots** the
steady-state required for the current submaximal workload before
settling. Magnitude depends on anticipation, anxiety, caffeine,
ambient temperature, and prior parasympathetic tone (HRV-baseline-
dependent).

**(b) Slow cardiac-output kinetics ("HR–VO2 lag").** Stroke volume
and the arteriovenous O2 difference rise faster than the working
muscle's local O2 demand can be matched, so for a brief overlap window
HR is being driven higher than the actual workload would dictate at
steady state. As the muscle's local circulation opens up (active
hyperaemia) and lactate-shuttle systems engage, HR settles to its
true steady-state value for the submaximal intensity. This is the
classic VO2 on-kinetics fast-phase, ~90–180 s in trained endurance
athletes.

**(c) Chest-strap dry-contact artefact.** Polar / Garmin / Wahoo HR
straps use two electrode pads requiring conductive contact (skin
moisture). In the first 1–3 minutes — before sweat establishes
proper conductivity — the signal is dominated by skin-electrode
impedance noise, **spuriously high BPM readings are common** (often
+20–40 bpm above the true value, sometimes much more). Polar's own
documentation requires moistening the electrodes before use; recovery
to a clean signal happens within minutes of sweat onset, not seconds.

### 2. The 10-minute exclusion convention

Friel's standard for aerobic-decoupling calculation (see
[compliance-decoupling-thresholds.md](compliance-decoupling-thresholds.md))
explicitly excludes the first 10 minutes of any session — not because
the data is "always wrong", but because the **three superimposed
transients above make HR-based inference unreliable in this window**.
Once steady state is reached (typically minute 8–12 for a moderate
warm-up start), HR reflects the workload it should reflect, and zone
or efficiency conclusions become valid again.

Operationally:

- **Zone time / Z-distribution:** exclude minute 0–10 before
  classifying time in zones.
- **Aerobic-decoupling (HR/pace or HR/power):** measure from minute 10
  onward, never from minute 0 (Friel standard).
- **Efficiency factor (EF), HR-recovery decoupling:** same exclusion.
- **Compliance against a planned HR target:** the planned target only
  starts to bind once the athlete is past minute 10. The convention
  in this framework is that **warm-up steps carry no HR target** in
  `intervals_icu` (see `config/training_paradigms.md`) — Garmin would
  otherwise fire false zone alarms during the very window where the
  transient artefact lives.

### 3. Why the early window appears in the lap data anyway

Lap chronicles (data-scientist output) **do** show the early HR
window — that is correct factual reporting and serves diagnostics
(e.g. recognising an unusually long startup phase that points to
under-recovery, OR confirming the strap took 4 minutes to settle today).
The error is downstream: when this lap data crosses from chronicle
into coaching feedback (coach-analyst output, athlete-facing message,
Strava insights), the early-window HR must be filtered out — it is
**measurement, not performance**.

### 4. What the early window does NOT tell us

- It does **NOT** mean the athlete "started too fast". Pace can be
  steady-state from second 1 — HR will still spike. Pace is the
  reference signal for early-exercise effort, not HR.
- It does **NOT** mean cardiovascular drift (which is the opposite
  pattern: HR rising over minutes 20–60+ at constant pace, driven by
  hyperthermia + dehydration + glycogen depletion).
- It does **NOT** indicate cardiac stress. A transient HR spike with
  rapid recovery is normal autonomic response. Stress markers are
  HR-recovery-time (failure to drop after exertion) and post-exercise
  HRV, not the onset transient.

### 5. When the early window IS diagnostically interesting

The early window is excluded from **coaching findings**, but stays in
the **diagnostic** layer:

- **Strap-contact debugging:** sudden spike >180 bpm in minute 1 at
  walking pace → reseat / wet the strap. A persistent rule-of-thumb:
  if minute-0–3 HR is implausible given the pace, the data quality
  is the story, not the athlete.
- **ANS state cross-check:** an unusually high onset overshoot at
  the same warm-up pace as last week may correlate with low HRV /
  poor recovery — but this is a **soft signal**, not a primary
  finding. The HRV-forecast model is the harder signal.
- **Anticipatory anxiety / pre-race adrenaline:** in race openings the
  onset overshoot can be very large; this is well-known and managed
  via warm-up routines, not via post-hoc HR complaints.

## Primary sources

| Author / Source | Year | Title | Venue / Link | Key quote |
|---|---|---|---|---|
| Whipp BJ, Wasserman K | 1972 | Oxygen uptake kinetics for various intensities of constant-load work | J Appl Physiol 33(3):351-356 | "Phase I (cardio-dynamic) on-kinetics — HR and Q rise faster than QO2, producing a transient mismatch in the first 1–2 min." |
| Bearden SE, Moffatt RJ | 2001 | VO2 and heart rate kinetics in cycling: transitions from an elevated baseline | J Appl Physiol 90(6):2081–2087 | Quantifies HR/VO2 kinetics asymmetry across baseline conditions. |
| Plews DJ, Laursen PB, Kilding AE, Buchheit M | 2013 | Heart rate variability in elite endurance athletes — current status and future directions | Int J Sports Physiol Perform 8(1):88–96 | Operational HRV/HR conventions for endurance athletes, including onset-period exclusion. |
| Friel J | 2009 | The Power Meter Handbook & TrainingPeaks Blog — Aerobic Decoupling | trainingpeaks.com — [Aerobic Endurance and Decoupling](https://www.trainingpeaks.com/blog/aerobic-endurance-and-decoupling/) | "Skip the first 10 minutes when calculating decoupling — HR has not yet stabilised." Operational standard adopted by the wider coaching community. |
| Polar Electro (product documentation) | n/a | H10 Heart Rate Sensor — User Manual | [polar.com](https://www.polar.com/en/sensors/h10-heart-rate-sensor) | "Moisten the electrodes of the strap before putting it on. Without proper contact, the signal may be erratic in the first minutes." |
| Achten J, Jeukendrup AE | 2003 | Heart rate monitoring — applications and limitations | Sports Medicine 33(7):517–538 | Reviews HR-monitoring artefacts including electrode contact, ambient temperature, hydration; warns against zone classification on early-exercise data. |
| Coyle EF, González-Alonso J | 2001 | Cardiovascular drift: new concepts | Exerc Sport Sci Rev 29(2):88-92 | Defines cardiovascular drift as the **late** rise (minute 20+) — distinct from the early-onset transient, often conflated. |

## Application in framework

- **`framework/agents/coach-analyst.md`** — MANDATORY exclusion rule
  for minute-0–10 HR in coach-output (no growth-area framing, no
  athlete-error phrasing, reject bad inputs from briefings). Links here.
- **`framework/agents/strava-publisher.md`** — early-window HR omitted
  from insights by default; if data is striking enough to acknowledge,
  name it with the technical term (Cardiac startup drift / HR-onset
  spike) and frame it as known kinetics, never as athlete error.
  Links here.
- **`framework/CLAUDE.md`** — Head-coach briefing rule: the head coach
  never lists minute-0–10 HR observations as findings in the briefing
  to coach-analyst or strava-publisher. Links here.
- **`framework/research/compliance-decoupling-thresholds.md`** — the
  10-minute exclusion is already encoded in decoupling-calculation
  caveats; this doc complements that by naming the underlying physiology
  and the chest-strap data-quality layer.
- **`config/training_paradigms.md`** — the existing rule "warm-up
  steps carry no HR target in `intervals_icu`" derives from the same
  phenomenon (the watch would alarm in the exact minute-0–10 window
  where the data is unreliable).

## Open questions / Caveats

1. **Trained vs. untrained kinetics:** Phase I cardio-dynamic kinetics
   are 90–180 s in trained endurance athletes (Whipp/Wasserman) but can
   extend to 4–6 min in deconditioned subjects. The 10-min convention
   covers the trained range with safety margin; for return-to-training
   after long pauses, a longer exclusion may be appropriate but is not
   currently coded.
2. **Strap-electrode artefact is brand- and skin-specific.** The
   10-min exclusion is generous enough for typical Polar / Garmin
   straps in dry winter conditions; in summer-sweat or with optical
   wrist-HR the dry-contact noise is less of an issue but the autonomic
   + cardiac-output components remain.
3. **Race-onset HR spike** is a special case where the overshoot is
   amplified by anticipation. Coaching guidance for race openings
   ("first km easier than goal pace") addresses this empirically; no
   need for a separate coaching rule beyond the existing exclusion.
4. **Indoor / virtual runs (VirtualRun, treadmill):** the chest-strap
   artefact still applies, but the central-command surge may be smaller
   (no environmental novelty). The 10-min exclusion still holds — no
   asymmetry needed by surface.
