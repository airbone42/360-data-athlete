# /pull — Fetch latest state from the configured git remote

Fetches and fast-forward-merges the configured default branch from `origin`
into the current working copy. Works against whatever remote is configured
(Gitea, GitHub, …) — the command itself is generic.

## Arguments
$ARGUMENTS
Optional: none.

---

## Workflow

```bash
# Resolve repo root from env or current working dir
REPO="${COACH_HOME:-$(pwd)}"
BRANCH="${GIT_DEFAULT_BRANCH:-master}"

git -C "$REPO" fetch origin "$BRANCH" 2>&1
git -C "$REPO" status --short
git -C "$REPO" pull --ff-only origin "$BRANCH" 2>&1
```

**Behaviour:**
- `--ff-only`: fast-forward only — aborts on divergence/conflicts.
- If the local branch has unmerged commits or the working tree is dirty →
  inform the athlete, do **not** overwrite, wait for a decision
  (rebase, stash, manual merge).

**Output to the athlete (compact):**
- Up to date: "Already up to date — no pull needed."
- Successful pull: short list of new commits
  (`git log --oneline HEAD@{1}..HEAD`).
- On error: show the error message verbatim and propose next steps.

**No auto-restart.** Changed scripts/configs take effect only on the next
athlete-triggered action — nothing reloads automatically.
