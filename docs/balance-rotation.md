# Balance rotation — cadence, placement and pool mechanics

Detail for the balance-rotation and pool-content rules under
[Feedback loop](../CLAUDE.md#feedback-loop) in CLAUDE.md. CLAUDE.md keeps the
auto-push rule, the S-rating requirement and the head-coach duties
(`--leg-conflict`, `--travel`); this file carries cadence and rotation
stepping, placement, manual invocation, the full pool-content rules and the
`--travel` / `--leg-conflict` mechanics of `get_balance_rotation.py`. Read it
when changing the cadence, editing `config/balance_pool.json`, or when a
travel or leg-conflict day needs the fallback details.

**Cadence is athlete configuration.** The framework default is 7 per week
(one per training day, the historical behaviour);
`balance_sessions_per_week` in `config/athlete_status.md` lowers it. Below 7
the push also enforces a minimum gap (`7 // n` days) and steps the A/B/C/D
rotation on from the previous session rather than picking by date — at a
two-day gap the date arithmetic keeps drawing the same keys. Set a lower
value when the balance work is a real prevention block: the programmes that
reduced lateral ankle sprains ran 2–3 progressive, perturbation-based
sessions per week, not a short daily drill.

**Placement.** The unit is scheduled before the day's earliest existing
session. Balance work belongs on fresh legs — the perturbation effect comes
from unfatigued sessions.
Manual invocation remains available for ad-hoc / preview purposes:

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/get_balance_rotation.py --date YYYY-MM-DD --show   # preview only
python3 "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/get_balance_rotation.py --date YYYY-MM-DD \
    | python3 "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/push_workouts.py --date YYYY-MM-DD --no-auto-balance
```

- Rotation A/B/C/D is `date.toordinal() % 4` at the daily default, and
  steps on from the previous session's key at any lower cadence
- `--show` previews without pushing
- Duration: 10–12 min, always as the third unit — existing workouts are
  not shortened
- Pool: `config/balance_pool.json`
- Opt-out: `push_workouts.py --no-auto-balance` only when explicitly
  justified (surgical recovery day, athlete-requested skip). Default is
  auto-on.

**Pool-content rules (policy):**
- **Every rotation entry MUST carry an S-rating column** (S1–S5,
  S1=stabil/easy, S5=umgefallen). Balance/proprioception sessions
  replace RPE with the stability rating — see the S-rating convention
  in `agents/specialist-complementary.md` (RPE-vs-S-rating rules).
  A rotation without explicit
  `Ziel: S{n}-S{m}` per exercise fails the convention and must be
  patched before the next push.
- **Leg-strength conflict awareness:** When today's plan already
  carries a `legs`-tagged WeightTraining workout (or the legacy
  `beine` tag on historical sessions), the head coach must inspect
  the chosen rotation before piping it into `push_workouts.py`.
  If the rotation contains posterior-chain-load exercises that would
  duplicate the strength block (e.g. Single-Leg RDL, heavy Step-up
  variants), either swap to a rotation that is leg-light, or apply
  the rotation's "if leg-strength already planned today" fallback
  if the pool entry carries one. Never push a duplicate Single-Leg RDL
  on top of a 14 kg+ strength SL RDL — the balance stimulus needs no
  load.
- **Next-day quality conflict awareness:** The same inspection duty
  covers the **following** day. Before the day's push, check whether
  tomorrow carries a leg-driven quality / long session (mesocycle table
  in `competition_plan.md` / weekly Hard-Reize outlook — same-day
  planning means it is not yet an intervals.icu event). If yes, pass
  `--leg-conflict` so the flagged slow-eccentric leg exercises are
  swapped mechanically (see "Leg-conflict routing" below). The athlete
  must receive a decided plan — shipping an unevaluated if-then
  addressed to themselves counts as a planning miss, not as delegation.
- **Equipment availability (travel / limited kit):** The pool contains
  equipment-dependent exercises (balance board, kettlebell loading, TRX),
  each declaring an `equipment` list and an optional `travel_fallback` in
  `balance_pool.json`. `get_balance_rotation.py
  --travel` (alias `--no-equipment`) swaps every equipment-dependent
  exercise for its pool-declared `travel_fallback` — e.g. a *balance-board
  single-leg + head-rotation* drill becomes *single-leg stand on an
  unstable soft surface (folded towel / cushion / soft mat) + head
  rotation*; a *KB-loaded reach* becomes an unloaded reach. An exercise
  with equipment but no declared fallback gets a generic single-leg /
  soft-surface substitute, flagged with a note in the output. The flag
  is forwarded end-to-end: `push_workouts.py --travel` passes it through
  to the auto-balance push. Default is off — the head coach passes
  `--travel` explicitly on travel / limited-kit days; nothing infers
  travel status automatically.
- **Leg-conflict routing (mechanized, coach-triggered):** Pool exercises
  that load the legs through a slow eccentric (TRX-assisted single-leg
  squat, slow step-down variants) declare `"leg_conflict": true` and an
  optional `leg_conflict_fallback` (same shape as the exercise entry).
  `get_balance_rotation.py --leg-conflict` — forwarded end-to-end via
  `push_workouts.py --leg-conflict` to the auto-balance push — swaps every
  flagged exercise for its declared fallback (a pure stability drill); a
  flagged exercise without a fallback gets a generic
  single-leg-stand-eyes-closed substitute, surfaced with a note. The
  output carries a visible mode marker. **Detection stays head-coach
  duty:** set the flag whenever today carries a leg-strength block OR
  tomorrow carries a leg-driven quality / long session — the next-day
  plan is often not an intervals.icu event yet, so nothing can infer the
  conflict mechanically. A conditional trailing note addressed to the
  coach is not a carrier for this rule — it goes out verbatim,
  unevaluated; express the conflict as `leg_conflict` flags + fallbacks
  in the pool.
