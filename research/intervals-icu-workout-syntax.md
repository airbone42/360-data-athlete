# Intervals.icu workout-builder syntax (step targets, repeats, cadence)

**Trigger:** two spec violations on `push_workouts.py` in real application:
1. Run step `Z2low 24m 122-130bpm` was accepted by intervals.icu, but the BPM-range suffix was **silently dropped** — the step landed without an HR target in the `workout_doc`.
2. Ride spin-up steps `Spin-up 15s 110rpm` without a watt target led on Wahoo plan upload to `422: each interval that is not of type 'repeat' must have a valid 'targets' array`.

---

## TL;DR

1. **Intervals.icu knows NO arbitrary BPM ranges in the workout syntax.** HR targets are expressed via **zone** (`Z2 HR`), **% LTHR** (`90-95% LTHR`) or **% MaxHR** (`70-75% HR`). A "122-130 bpm" notation is parsed, but the suffix is ignored — the step ends up without a target in the `workout_doc`. Sub-zones must be converted via the appropriate % ratio (e.g. Z2 lower half at LTHR 160: 122/160 = 76% to 130/160 = 81% → `76-81% LTHR`).

2. **Every non-repeat step must carry at least ONE "real" target** (watt, HR, pace, zone) — cadence alone is NOT enough. Wahoo plan upload validates this strictly and fails with 422. Frequent trap: spin-ups ("just bring rpm up") → still need a watt anchor, e.g. `Spin-up 15s 240W 110rpm`.

3. **Consistent target source per workout:** indoor ride → watt targets (with cadence). Run → HR targets OR pace OR zone. Mixing works ("Z1 HR" on bike), but on smart-trainer plan upload (Wahoo, Zwift) occasionally leads to edge cases — if the stimulus is power-driven, always set watts.

---

## Full syntax reference (intervals.icu workout builder)

### Duration

| Format | Example | Meaning |
|--------|---------|---------|
| `Xh` | `1h` | Hours |
| `Xm` | `10m`, `5m` | Minutes |
| `Xs` | `30s`, `90s` | Seconds |
| `XhYmZs` combined | `1h5m`, `5m30s` | Combination |
| Short form | `5'`, `30"`, `1'30"` | Apostrophe = min, double-quote = sec |
| `press lap` | `Warm-up jog 8m press lap` | Step until manual lap press (watch); additionally default duration for the intervals.icu plan display |

**⚠️ Trap: `m` = minutes.** For meters use `mtr` (`500mtr`, not `500m`).

### Distance

- Metric: `500mtr`, `2km`, `10km`
- Imperial: `1mi`, `4.5mi`

### Power targets

| Format | Example | Meaning |
|--------|---------|---------|
| Absolute watt | `220w`, `200-240w` | Fixed watt anchor (range allowed) |
| % FTP | `75%`, `95-105%` | Percent of FTP |
| Power zone | `Z2`, `Z3-Z4` | Power-zone reference |
| MMP | `60% MMP 5m` | % of Mean Max Power over X minutes |
| Ramp | `10m ramp 50%-75%` | Linear power rise across the step duration |

### HR targets

| Format | Example | Meaning |
|--------|---------|---------|
| % MaxHR | `70% HR`, `75-80% HR` | Percent of MaxHR |
| % LTHR | `95% LTHR`, `90-95% LTHR` | Percent of threshold HR |
| HR zone | `Z2 HR`, `Z2-Z3 HR` | HR-zone reference |

**⚠️ Arbitrary BPM range (`126-135 bpm`) is NOT supported.** Workouts are portable between athletes — intervals.icu therefore enforces relative targets. If a BPM range is desired: convert into % LTHR or % HR.

### Pace targets

| Format | Example | Meaning |
|--------|---------|---------|
| Absolute | `5:00/km Pace`, `3:00/100m-4:00/100m Pace` | Pace per km or per 100m (swim) |
| % | `60% Pace`, `78-82% Pace` | % of threshold pace |
| Pace zone | `Z2 Pace` | Pace-zone reference |

### Cadence

- Append after the target: `- 10m 75% 90rpm` or `- 12m 85% 90-100rpm`
- Cadence alone WITHOUT power/HR/pace is NOT a valid step target (see the Wahoo validation trap above)

### Special keywords

- `freeride` — disables ERG mode on smart trainers, e.g. `20m freeride`
- `press lap` — see Duration above

### Repeat blocks

Two notations:
```
Main Set 5x
- Hart 30s 390w
- Locker 60s 150w
```
or
```
5x
- Hart 30s 390w
- Locker 60s 150w
```

Nested repeats are NOT supported — anyone wanting to write 2×8 with 3 min set rest must spell out the sets individually (Set1 8x / set rest / Set2 8x).

### Free text

Text before the first duration becomes the step cue (watch display).
- `- Warmup 10m 60%` → watch shows "Warmup" + power target
- `- Hart 30s 390w 95-100rpm` → watch shows "Hart" + power + cadence

---

## Traps found (drift incidents from real application)

### Trap A: arbitrary BPM range silently dropped

**Push attempt:**
```
Main
- Z2low 24m 122-130bpm
```

**What intervals.icu makes of it:**
```json
{"text": "Z2low", "duration": 1440}
```
→ NO `hr` field, step has **no HR target** — athlete gets on the watch only a 24-min step without HR display.

**Fix:**
```
- Z2low 24m 76-81% LTHR
```
At LTHR 160 this corresponds to 122-130 bpm (Z2 lower half). The step now carries `hr: {units: hr_lthr, start: 76, end: 81}`.

### Trap B: spin-up with only cadence — Wahoo 422

**Push attempt:**
```
- Spin-up 15s 110rpm
```

**Wahoo plan-upload response:**
```
422: Plan validation error: each interval that is not of type 'repeat' must have a valid 'targets' array
```

Cadence alone is not a target. On a smart-trainer **Ride**, Wahoo needs a
**power** target specifically (see Trap B-bis) — cadence-only or HR-only is
not enough.

**Fix:**
```
- Spin-up 15s 200W 110rpm
```

Watt anchor for the spin-up phase (~80% FTP at FTP 250 W) — the athlete cranks the frequency up AND drives a minimum power, which is also the intended goal.

### Trap B-bis: HR-only target on a Ride — same Wahoo 422 (recurrence)

**Push attempt** (indoor Ride warm-up / set-rest / cool-down written with HR
zones, the way a Run would be):
```
- Warmup 9m Z1 HR 90-100rpm
- Recovery 3m Z1 HR
- Cool-down 8m Z1 HR 85-90rpm
```

**Wahoo plan-upload response:** the identical
`422: ... each interval that is not of type 'repeat' must have a valid 'targets' array`.

intervals.icu happily accepts `Z1 HR` on a Ride (it counts as a target), so
this is **invisible to a naive target-presence check** — the failure only
surfaces downstream at the Wahoo smart-trainer sync, which expects a **power**
target on a ride and treats an HR-only target as no target. (After a hard
30/15 interval an HR-Z1 target is physiologically pointless anyway — HR lags
the effort by 5-10 min.)

**Fix:** every Ride step carries watts; HR/cadence may ride along as
secondary but never alone.
```
- Warmup 9m 150W 90-100rpm
- Recovery 3m 150W
- Cool-down 8m 130W 85-90rpm
```

**Validator enforcement (R012, since this recurred):** `validate_plan.py`
now distinguishes *any* target from a *power* target on Ride/VirtualRide
steps. A Ride step whose only target is HR/pace (`Zn HR`, `% LTHR`,
`% HR`) is flagged **ERROR** (`POWER_PATTERNS_RIDE` check) — it blocks the
push before the workout can reach the Wahoo sync. Regression test:
`tests/test_validate_plan_r012_ride_power.py`.

### Trap C-bis: blank line inside the repeat block — reps=1 instead of reps=N

**Push attempt:**
```
Strides 5x

- Stride 20s

- Easy 90s Z1
```

**What intervals.icu makes of it:**
```json
{"text": "Strides 5x", "reps": 1, "steps": [{"text": "Stride", "duration": 20, ...}, {"text": "Easy", "duration": 90, ...}]}
```
→ The repeat block ends up with `reps=1` instead of `reps=5`. Athlete gets on the watch **only one** stride instead of five. Total workout duration does not match the plan (3110s instead of 3550s). Silent drift — no server error.

**Fix:**
```
Strides 5x
- Stride 20s
- Easy 90s Z1
```

Simple newlines (`\n`) between the repeat header and its items. A blank line (`\n\n`) ONLY between different blocks (Warmup ↔ Main ↔ Strides ↔ Cool-down). Adjacency between the `Nx` header and the `-` bullets is the only marker by which the server parser recognises the repeat block.

### Trap D: bare `Zn` on Run — silently dropped as Power zone

**Push attempt (Run):**
```
- Trab Easy 2m Z1-Z2
- Easy 90s Z1
```

**What intervals.icu makes of it:**
- `Zn` (or `Zn-Zm`) WITHOUT the explicit `HR` or `Pace` suffix is
  interpreted as a Power-zone reference. Power zones are a bike concept;
  for Run the parser drops the suffix and the step lands without any
  target.
- Athlete sees only "Trab Easy" / "Easy" on the watch — no HR
  guidance. The plan view shows the step at base intensity (no zone
  bar).

**Fix:**
```
- Trab Easy 2m Z1-Z2 HR
- Easy 90s Z1 HR
```

Or use the `% LTHR` / `% HR` notation (precise corridor). Bare `Zn`
is valid ONLY for Ride/VirtualRide (where it refers to the Power zone
explicitly). Validator R012 catches this on Run as ERROR.

### Trap E: dash-prefixed repeat header — degraded to list item

**Push attempt:**
```
Main
- 4x
- Threshold 5m 92-100% LTHR
- Trab Easy 2m Z1-Z2 HR
```

**What intervals.icu makes of it:**
- The header line `- 4x` looks like a list item (leading `-`), not a
  repeat-block header. The parser does not open a repeat scope.
- The next `- Threshold ...` and `- Trab Easy ...` items become
  adjacent top-level steps, not loop body.
- Total volume silently degrades from 4×(5m+2m)=28m to 5m+2m=7m. The
  athlete gets two single steps instead of four interval pairs.

**Fix:**
```
Main
4x
- Threshold 5m 92-100% LTHR
- Trab Easy 2m Z1-Z2 HR
```

Header is **standalone**, no dash. The optional cue (e.g.
`Main Set 5x`, `Strides 2x`) goes on the same line, again without a
leading dash. Validator R013 catches dash-prefixed headers as ERROR.

### Trap F: tilde-prefix on press-lap duration → step silently dropped

**Push attempt** (well-intentioned attempt to make the duration hint
visible on Garmin):
```
- Easy ~5m press lap
- Cool-down ~5m press lap
```

**What intervals.icu does:**
- The leading `~` makes the duration token unparseable. Rather than
  treating `~5m` as cue text and falling back to `press lap`, the
  intervals.icu server **silently drops the entire step from
  `workout_doc`**. The step is gone — not just degraded.
- Athlete-visible damage: the warmup easy-jog step (and/or cool-down
  step) is completely missing on Garmin. The athlete gets the
  description-text but no executable step.

**Fix:**
```
- Easy 5m press lap
- Cool-down 5m press lap
```

Classical form. The `5m` lives only in the intervals.icu plan view,
NOT as a Garmin cue. To communicate the duration estimate to the
athlete, use the `structure` description text (`coaching_notes` or
the `description` block visible in intervals.icu and Strava).
**Investigated and rejected approaches:** leading `~`, leading `ca.`,
duration in cue (`Easy 5min press lap`) — all either drop the step
or have undefined parser behaviour. The intervals.icu syntax does
not currently support a "press-lap with visible Garmin duration"
combination.

**Open follow-up:** if intervals.icu adds explicit Garmin cue-text
support for press-lap steps in the future, revisit. Until then,
the description-text + plan-view duration is the only stable way.

### Trap G: zone tokens inside cue free text — silent power-zone tagging

**Push attempt** (cue mentions a zone for context):
```
- Calf raises easy 1m — 2×10 bodyweight, neuromuskuläre Wake-up vor Z4
```

**What intervals.icu does:**
- The server parser sees `Z4` anywhere on the step line and treats
  it as a target token. For a Run/VirtualRun step that has no real
  target, it lands as `power: {units: 'power_zone', value: 4}` in
  `workout_doc`. Garmin then displays a Power-Z4 target on a Run —
  nonsensical and confusing.
- The em-dash separator is NOT respected by the intervals.icu
  parser (only by our local validator R012 catch).

**Fix:**
- Drop zone tokens from cue free text. Paraphrase: "vor dem
  Quality-Block", "vor den Intervallen", "Wake-up vor der Hauptbelastung".
- Reserve `Zn HR` / `% LTHR` / `% HR` / `Zn` notations exclusively
  for the structural target slot of a real loaded step.

### Trap C: indoor-ride cool-down with only HR zone

**Push attempt:**
```
- Cool-down 6m Z1 HR 85rpm
```

`Z1 HR` for run HR zones is OK on intervals.icu, but at the Wahoo plan upload of an indoor ride this can also fail depending on the setting, because the smart trainer expects watt targets. Also: after a 30/15 stress an HR target in Z1 (≤125) is physiologically nonsensical anyway — HR needs 5-10 min to drop.

**Fix:**
```
- Cool-down 6m 130W 85rpm
```

Watt anchor (~43% FTP, easy spinning), cadence hint. HR may drop passively.

---

## Application in framework

1. **`framework/scripts/validate_plan.py`** — new rule `R012`:
   - Parse the `intervals_icu` field of every workout
   - For every non-header step check: is there at least one "real" target (watt, HR-zone/LTHR/HR, pace-zone/pace/absolute)?
   - Cadence alone is NOT a target → ERROR
   - Suffix `XX-YYbpm` or `XXbpm` without `% LTHR` / `% HR` / `zone` token → ERROR (silent-drop trap)
   - **Severity ERROR** (blocks push) — the errors are silent (Trap A) or server-422 (Trap B).

2. **`framework/agents/specialist-endurance.md`** — new self-check obligation "Workout-syntax self-check":
   - Before the JSON output, check that every non-header step in the `intervals_icu` carries a target token
   - Phrase HR ranges only as `zone`, `% LTHR`, `% HR` — NEVER as `XX-YYbpm`
   - Indoor-ride steps ALWAYS carry a watt target (also spin-ups, cool-downs, easy rest steps)

3. **`framework/research/`** — this document as reference for future discussions about workout-syntax options.

---

## Primary sources

| Author / year | Title | Link | Key quote |
|---------------|-------|------|-----------|
| David Federman (intervals.icu maintainer) — 2024 | Workout Builder Syntax Quick Guide | [forum.intervals.icu/t/workout-builder-syntax-quick-guide/123701](https://forum.intervals.icu/t/workout-builder-syntax-quick-guide/123701) | Full target-syntax cheat-sheet |
| Intervals.icu Forum Thread — 2024 | Custom Heart Rate range planned workout | [forum.intervals.icu/t/custom-heart-rate-range-planned-workout/72460](https://forum.intervals.icu/t/custom-heart-rate-range-planned-workout/72460) | "workouts are portable between athletes" → no arbitrary BPM ranges |
| Wahoo API spec / 422 response | (error session from real application) | inline error: `"each interval that is not of type 'repeat' must have a valid 'targets' array"` | every non-repeat step needs a target |

---

## Open questions / Caveats

- **MaxHR vs LTHR % HR:** the forum snippet says `70-80% HR` = % MaxHR, but other sources use `% HR` ambiguously (sometimes % LTHR). **We use in the framework exclusively `% LTHR`** for HR ranges, because LTHR is documented in the athlete profile (`athlete_status.md`). `% HR` (= % MaxHR) is only used when MaxHR is explicitly available AND validated.

- **Wahoo validation vs. intervals.icu validation:** intervals.icu is more permissive — it accepts steps without a power target and without an HR target and produces "freeform" steps. Wahoo plan upload validates more strictly and needs real targets. If our workouts are to be pushed to a Wahoo smart trainer (`paired_event_id` populated), every step MUST have a target.

- **Press lap** is not in the official cheat-sheet, but works (cache evidence from multiple intervals.icu workout imports). Presumably an unlisted feature — observe behaviour.
