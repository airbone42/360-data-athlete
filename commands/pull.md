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

**Submodules** (e.g. the framework, when the repository embeds it). A pull
moves the commit a submodule is recorded at, not its checkout, so the coach
would keep running the old code without any signal. Check each submodule
out at the recorded commit — but only when it is **behind** it. A submodule
ahead of the recorded commit carries work whose pointer bump is still
pending, a diverged one needs a human; checking the recorded commit out in
either case would silently revert that work.

```bash
if [ -f "$REPO/.gitmodules" ]; then
  git -C "$REPO" config -f .gitmodules --get-regexp '^submodule\..*\.path$' |
  while read -r key path; do
    name=${key#submodule.}; name=${name%.path}
    rec=$(git -C "$REPO" rev-parse "HEAD:$path" 2>/dev/null) || continue
    if [ ! -e "$REPO/$path/.git" ]; then          # not initialised yet
      git -C "$REPO" submodule update --init -- "$path" 2>&1
      continue
    fi
    cur=$(git -C "$REPO/$path" rev-parse HEAD)
    [ "$rec" = "$cur" ] && continue
    git -C "$REPO/$path" cat-file -e "$rec^{commit}" 2>/dev/null ||
      git -C "$REPO/$path" fetch --quiet origin
    if git -C "$REPO/$path" merge-base --is-ancestor "$cur" "$rec" 2>/dev/null; then
      git -C "$REPO" submodule update --init -- "$path" 2>&1
      # Re-attach the branch where that rewrites nothing, so the next commit
      # made in the submodule does not land on a detached HEAD.
      br=$(git -C "$REPO" config -f .gitmodules --get "submodule.$name.branch" || echo main)
      tip=$(git -C "$REPO/$path" rev-parse --verify --quiet "refs/heads/$br") &&
        git -C "$REPO/$path" merge-base --is-ancestor "$tip" "$rec" &&
        git -C "$REPO/$path" branch --quiet -f "$br" "$rec" &&
        git -C "$REPO/$path" checkout --quiet "$br"
      echo "$path: ${cur:0:7} -> ${rec:0:7}"
    else
      echo "⚠️ $path is ahead of or diverged from the recorded commit — left alone"
    fi
  done
fi
```

**Behaviour:**
- `--ff-only`: fast-forward only — aborts on divergence/conflicts.
- If the local branch has unmerged commits or the working tree is dirty →
  inform the athlete, do **not** overwrite, wait for a decision
  (rebase, stash, manual merge).
- A submodule that was left alone is reported with its name — never forced.

**Output to the athlete (compact):**
- Up to date: "Already up to date — no pull needed."
- Successful pull: short list of new commits
  (`git log --oneline HEAD@{1}..HEAD`), plus any submodule that moved
  (old → new commit) or was left alone.
- On error: show the error message verbatim and propose next steps.

**No auto-restart.** Changed scripts/configs take effect only on the next
athlete-triggered action — nothing reloads automatically.
