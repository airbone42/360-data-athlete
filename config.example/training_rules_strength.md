# Training rules — strength / plyo / ninja specialist

## Intensity control (hard brake)
- TSB < −20: immediately reduce to Z1 or rest day (mandatory, even if
  the plan says otherwise)

## Plyo as a standalone session
- 48 h gap to intervals (legs / CNS recovery)
- Long run (>60 min) yesterday: only light plyo as a warmup

## Interference distance to the run (double day)
- WeightTraining (without leg focus) → run: **≥3 h** (`workout_parser.py`
  enforces this automatically)
- WeightTraining with leg focus (`legs` / `plyo` tags) → run: **≥6 h**
- Order is fixed: strength / plyo ALWAYS before the run

## Feedback-based load control (RPE autoregulation)

Analyse athlete messages and descriptions from the last sessions of
this type:

**Signals for RPE ≤ 7** ("easy", "light", "more weight", "too little",
"too easy"):
→ progressive overload: weight +2.5–5 % OR reps +1–2 OR next
   complexity level

**Signals for RPE 8** ("good", "fits", "OK", "tough but doable",
"perfect"):
→ hold: same weights and reps

**Signals for RPE ≥ 9** ("hard", "heavy", "DOMS", "couldn't",
"abandoned", "too much"):
→ deload: volume −20 % or weight −10 %

**No feedback present**: plan conservatively, slightly under the last
known level.

## Plyo progression model (Markovic & Mikulic, 2010)
- Level 1 (basics): bilateral — box jumps, squat jumps, broad jumps
  (40–60 ground contacts)
- Level 2 (intermediate): unilateral — single-leg hops, split squat
  jumps (30–40 contacts)
- Level 3 (expert): reactive / depth jumps — drop jumps, bounding
  (20–30 contacts)
→ Move to the next level only when feedback on the current level
  signals "easy".

## intervals.icu description formatting

In `description` sections (WARM-UP, MAIN, COOL-DOWN), separate with
`\n\n`, and prefix each exercise with `\n\n` — intervals.icu does not
render single `\n` as a line break.

## Static stretching — defaults
- **Hold time: 30 s per side** (sweet spot from the literature; longer
  holds provide no added value for trained athletes and are poorly
  tolerated)
- Maximum hold: 30 s — not 45 s, not 60 s
- No redundant stretches: pick one variant for the same muscle group
  - Piriformis stretch = figure-4 stretch (identical) — only one per
    session
  - 90/90 hip stretch ≠ piriformis (different orientation; both OK in
    one session)
- Cool-down: max 3–4 stretches, each 30 s/side
