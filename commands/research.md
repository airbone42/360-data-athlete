# /research — Evidence research for a flagged uncertainty

Resolves a concrete sport-science question with verifiable evidence and
persists the finding to `framework/research/`. Two entry points:

- **(a) Flag-driven** — a coach agent emitted a `🔬 RESEARCH-FLAG` (see
  `framework/CLAUDE.md` → "Research-before-scaling-or-new-protocol" → agent
  side) and the athlete approved the research.
- **(b) Direct** — the athlete runs `/research <question>`.

## Arguments
$ARGUMENTS
Optional. The research question (free text). If empty, the question is taken
from the approved `RESEARCH-FLAG` block currently on the table.

---

## Workflow

### Step 1: Assemble the research brief

Collect:
- **question** — athlete-agnostic, one concrete sport-science question (from
  the flag's `question` field or the `$ARGUMENTS` text).
- **context** — what coaching decision is gated (from the flag's
  `decision_blocked` / `uncertainty`, or the surrounding conversation).
  Background only — it must not be transcribed into the persisted document.
- **date** — `$(date +%Y-%m-%d)`.

### Step 2: Launch research-analyst as subagent (fresh context)

Launch the `aicoach-framework:research-analyst` agent **as a subagent (Task
tool)** — never inside the active coach pane — to guarantee fresh context.
Pass `question`, `context`, and `date`. The agent:

1. Checks `framework/research/` first; reuses an existing doc if it covers the
   question (no duplicate).
2. Otherwise researches via `WebSearch` / `WebFetch` (primary literature
   first).
3. Persists `framework/research/<topic-slug>.md` to the schema in
   `framework/research/README.md`, athlete-agnostic (no dated incident
   anchors, no athlete data points).
4. Updates the index table in `framework/research/README.md`.
5. Returns TL;DR + key sources + derivation + proposed downstream edits.

### Step 3: Present the research feedback to the athlete

Show the agent's summary block 1:1: **what** was researched (sources),
**what was derived** (TL;DR + the consequence for the gated decision), and the
**proposed downstream edits**. This is the athlete-facing answer to "what did
you research and what did you conclude".

### Step 4: Apply downstream edits — after explicit approval

Per proposed edit, ask the athlete (one yes/no, no option menu):

- **`config/*` edits** (athlete-specific application of the finding) →
  route through `config-fixer` (Task tool, fresh context, approval log in
  `data/approvals/`).
- **`framework/` edits** (`training_paradigms.md` defaults, an `agents/<x>.md`
  rule, a paradigm number annotated with the new research reference) → apply
  directly via Edit, keeping the sphere discipline (generic only).

When the finding **confirms** the current paradigm: no edit — note it and move
on.

### Step 5: Commit (framework sphere)

The research document and any `framework/` edits are framework-generic — commit
in the submodule and push, then bump the submodule pointer in the wrapper:

```bash
# in the framework submodule
git -C framework add research/ agents/ commands/ CLAUDE.md
git -C framework commit -m "feat(framework): research <topic> — <hook>"
git -C framework push

# in the wrapper: bump the submodule pointer
git add framework
git commit -m "chore(personal): bump framework — research <topic>"
```

Auto-push applies per the wrapper convention. Athlete-specific `config/` edits
from step 4 are a **separate** wrapper commit (`fix(config): …`) — never mix
spheres in one commit.

### Step 6: Re-entry into the interrupted flow

If the flag interrupted a `/training` (or `/analyse`) flow, re-brief the
agent that raised it — now with the new `framework/research/<topic-slug>.md`
as a citation anchor — and continue where the flow paused. The research must
reach the decision it was meant to unblock; do not persist the doc and forget
the original question.

---

## Notes

- `/research` is **agent- and web-search-based** — it invokes no Python
  scripts. (If a script call ever becomes necessary, use the
  `"${CLAUDE_PLUGIN_ROOT:-.}"/scripts/…` form — bare `python3 scripts/…` is
  blocked by `tests/test_plugin_manifest.py`.)
- Idempotency: a re-run of the same question finds the freshly persisted
  document and reuses it instead of writing a duplicate.
- Gating discipline lives upstream: the head coach only reaches `/research`
  **after** the athlete approved a flagged uncertainty (or the athlete invoked
  it directly). The flag itself never auto-runs research — see the gating rule
  in `framework/CLAUDE.md`.
