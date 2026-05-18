# /audit — Consistency audit of the knowledge base

Scans the coach system for contradictions between `config/` files,
sub-agents, prompts, the exercise mapping, and external sources
(intervals.icu NOTEs, Strava). Findings are refined by the
`config-auditor` (fresh context) and written as a markdown report to
`data/audits/`. Fixes go through the `config-fixer` (fresh context)
after athlete approval.

## Arguments
$ARGUMENTS
Optional: `--offline` (skip intervals.icu + Strava roundtrip — faster,
but NOTE drift and shoes are not checked).

---

## Workflow

### Step 1: Run the mechanical scanner

Default is online — the most important drift sources (NOTE-vs-static,
Strava shoes) need API access.

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/audit_consistency.py > /tmp/audit_raw.json
```

For `--offline` in arguments:
```bash
python3 "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/audit_consistency.py --offline > /tmp/audit_raw.json
```

Check `online_error` in the JSON. If present → inform the athlete and
continue with the available findings.

### Step 2: Launch config-auditor as subagent

Launch the `config-auditor` agent **as a subagent (Task tool)** to
guarantee fresh context — not inside the active coach pane.

In the prompt, pass:
- Path `/tmp/audit_raw.json` (or the JSON content directly, if small)
- Current date for the output path
- Mode (online/offline)

The auditor:
1. Reads the scanner JSON
2. Refines each finding semantically (drop, severity adjustment, context
   enrichment)
3. Adds its own semantic checks (phase-vs-restriction, LTHR drift,
   mapping plausibility, equipment match, exercise-log drift, recovery
   week activities)
4. Writes a report to `data/audits/YYYY-MM-DD-HHMM-audit.md`
5. Returns a compact summary (HIGH/MEDIUM/LOW counts + top HIGH findings)

### Step 3: Present summary

Show the athlete the auditor summary 1:1, plus the report path. Ask:

> "Which findings should I fix? (e.g. 'F001, F003' or 'all HIGH' or
> 'nothing')"

### Step 4: Fixes via config-fixer (fresh context)

Per finding (or batch of identical category):

1. Read the YAML block of the finding from the audit report
2. Launch `config-fixer` **as a subagent (Task tool)** with the YAML
   block + audit-report path
3. The fixer presents the diff in chat, gets explicit approval,
   implements via Edit, verifies, marks the finding in the report as
   `✅ FIXED`
4. On "different" or "no" — the fixer marks as `⏭ SKIPPED`

When the athlete says "all HIGH": launch the fixer for all HIGH findings
sequentially (not parallel — edits can invalidate each other).

### Step 5: Optional re-run

After fixes: suggest running `/audit` again — idempotency should hold
(fixed findings should not reappear).

### Step 6: Commit

When the fixer is done: remind the athlete to commit (the head coach
does this, not the fixer):

```bash
git add -A
git commit -m "fix(audit): F00X, F00Y — <short description>"
```

---

## Reproducibility

- Scanner output is deterministic given the same input (same configs +
  same intervals.icu data → identical JSON)
- Audit reports are persisted with timestamps (`data/audits/`) and
  committed — audit history is preserved
- Auditor + fixer are subagents → fresh context guaranteed, no pollution
  from the active coach session

## Extending the scanner

New drift types → add a `check_<name>` function in
`scripts/audit_consistency.py`, register in `CHECK_MAP`. The auditor
knows the schema dynamically (it reads all `findings`).
