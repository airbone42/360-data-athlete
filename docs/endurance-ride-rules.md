# Endurance specialist — ride and indoor-ride rules

Detail for `agents/specialist-endurance.md` when the directive `type` is
`Ride` / `VirtualRide`, or a bike session with `indoor: true`. The agent keeps
the non-negotiables in short (watt target instead of HR-only steps, watts +
RPE steer, bike HR zones below run zones, ~100 % MAP for 30/15 and 30/30, ERG
power is a prescription and never a stop criterion or a finding); this file
carries the full rules, the step formats and the indoor-ride example. Read it
before writing the `intervals_icu` text of a ride.

## Indoor-ride intensity steering

For indoor cycling, **power (Watt) + RPE are the primary anchors**, HR is
secondary. Reasons:

- Indoor HR drifts upward without airflow (sometimes 5–10 bpm vs. outdoor
  same effort) — using a strict HR ceiling makes Z2 sessions feel
  artificially hard.
- For runner-cyclists, **cycling HR-zones are typically 5–10 bpm lower
  than running zones** at the same metabolic intensity; never reuse the
  run-LTHR zone bounds 1:1 on the bike.

Read athlete-specific anchors from `config/athlete_status.md`:
- `Rad-Leistungsanker` (FTP, Z2-Watt, Threshold-Watt, Sprint-Watt) — if
  present, prescribe in Watt and quote the RPE band.
- `Rad-HF-Korrektur` (run-LTHR offset) — if present, derive bike Z2/Z3
  ceiling from the offset rather than from `context.hrZones` directly.

When neither is documented: cap Z2 at "run-Z2 minus ~10 bpm" as a
conservative default, prescribe RPE (Z2 = RPE 3–4), and ask the athlete
to update `athlete_status.md` with the validated bike anchors.

## 30/15 and 30/30 blocks, ERG control, inter-set rest

- **30/15 and 30/30 short-rep blocks (Rønnestad/Billat) — intensity:**
  target **~100 % MAP (≈ 105–120 % FTP)**, the MAP/VO2max-power zone —
  not 130–145 % FTP. Pushing the work reps above MAP is the
  "intensified short intervals" trap: it *reduces* time ≥ 90 % VO2max
  rather than raising it (Frontiers 2024). Athlete-specific watt/MAP
  anchors live in `config/athlete_status.md`; read them from there.
  **Research anchor:** [vo2max-short-intervals.md](../research/vo2max-short-intervals.md).
- **⛔ On an ERG-controlled smart trainer, power is a prescription and not
  a measurement — never build a stop criterion or a finding on it.** The
  trainer holds target watts regardless of how the athlete is coping, so
  a rule like "end the set when a rep drops below X W" cannot fire until
  they have stopped pedalling altogether — long after the decision was
  due. The same artefact runs the other way in analysis: "power held to
  the last rep", "zero decay across every interval" describes the device
  doing its job, and must never be reported as a strength or cited as
  evidence of adaptation. Check `config/equipment.md` for the trainer and
  its control mode before writing either a bike stop criterion or a bike
  analysis. Where the mode is unknown, assume ERG for any indoor
  structured session and say what you assumed.
  - **Steer and evaluate on cadence, HR and RPE.** Cadence is the variable
    that carries muscular capacity under ERG: when the athlete runs out,
    cadence falls while the power trace stays flat. Recovery-interval
    cadence tends to break before work-interval cadence — worth logging as
    the earlier signal, but as an observation rather than a validated
    threshold. Per-athlete numbers belong in `config/athlete_status.md`
    with the sample size they came from.
  - **Power remains the correct dose.** Watt anchors (MAP, FTP
    percentages, per-format targets) are how the session is prescribed and
    stay in the plan. Only the inference back from held watts to athlete
    state is invalid.
  - On a non-ERG setup (slope/level mode, rollers, outdoor) power *is* an
    athlete signal and the usual work-power criterion applies.
- **30/15 — inter-set recovery duration:** default **3 min** between
  sets (Rønnestad baseline — the research-backed *lower bound*, not a
  fixed rule). Extend to **4 min** when the session sits at the upper
  end of the volume curve (**≥ 4 sets OR ≥ 9 reps/set**) OR the prior
  same-protocol session was reported breathing/cardio-limited in the
  last sets — extra set rest restores PCr + ventilation so the next set
  hits MAP cleanly without blunting the stimulus (time ≥ 90 % VO2max is
  accumulated *inside* the sets, not during the rest; the "more rest
  hurts" finding applies only to the 15 s within-set micro-rest, never
  to set rest). Cap at **5 min**. Progress one variable at a time —
  don't raise volume AND tighten rest in the same step. Optional HR
  autoregulation cue in `focus`: clear to start the next set once HR
  drops to ~65–70 % HRmax. **Research anchor:**
  [vo2max-short-intervals.md](../research/vo2max-short-intervals.md) §4b.

## Step formats for indoor rides

- **Warmup — indoor ride (`type: Ride` + `indoor: true`):** no `press
  lap` (athlete is already on the trainer, no decision moment). Fixed
  time step with a **power (watt) target — not an HR-only target**. A
  smart-trainer plan upload rejects HR-only steps on an indoor ride
  (422); validator R012 blocks this before push. Format:
  `- Warmup Xm <W>W` (e.g. `- Warmup 10m 140W`). Cadence optional:
  `- Warmup Xm <W>W 85-90rpm`. A bare power zone (`Z1`) is also
  accepted as a power target; `Z1 HR` is not.

- **Cool-down — indoor Ride:** no `press lap`, fixed time step with a
  **power (watt) target — not HR-only** (same R012 reason as the indoor
  warmup). Format: `- Cool-down Xm <W>W` (e.g. `- Cool-down 8m 120W`).

- **Cadence (bike):** `Xrpm` or `X-Yrpm` after the target when useful.

## Example: indoor ride output

**Example for indoor ride (no `press lap`, fixed times + power target; illustrative values):**

```json
{
  "structure": [
    {"step": "Warm-up", "duration_min": 7, "description": "Easy spin, 85-90 rpm"},
    {"step": "Main", "duration_min": 23, "description": "Z2 steady"},
    {"step": "Cool-down", "duration_min": 5, "description": "Easy spin"}
  ],
  "intervals_icu": "Warmup\n- Warmup 7m 140W 85-90rpm\n\nMain\n- 23m 180W\n\nCool-down\n- Cool-down 5m 120W",
  "focus": "..."
}
```
