#!/bin/bash
# Local mirror of .github/workflows/test.yml — run before every push so a
# red CI is never the first place a failure shows up.
#
#   bash scripts/ci_local.sh            # all checks, ruff advisory (like CI)
#   CI_LOCAL_STRICT=1 bash scripts/...  # ruff failures become blocking
#
# Mirrors the workflow's two jobs:
#   test (matrix 3.11 + 3.12):  ruff check .  +  pytest tests/
#   validate-plugin:            manifest JSON + required name field
# Matrix legs whose interpreter is not installed locally are reported as
# SKIPPED — CI still covers them, but the skip is loud, never silent.
set -u
cd "$(dirname "$0")/.."

fail=0

# Resolve an interpreter that actually runs. Probing for the command is not
# enough: on Windows `python3` is commonly a Microsoft Store stub that prints an
# install hint and exits non-zero, so a manifest check running through it fails
# while the manifests are perfectly valid. Execute a no-op to tell a real
# interpreter from a launcher shim.
PY=""
for cand in python3 python python3.12 python3.11; do
  if command -v "$cand" >/dev/null 2>&1 && "$cand" -c "" >/dev/null 2>&1; then
    PY="$cand"
    break
  fi
done
if [ -z "$PY" ]; then
  echo "❌ no working python interpreter found — cannot mirror CI"
  exit 1
fi

echo "── validate-plugin ──────────────────────────────────────────"
"$PY" -c "import json; json.load(open('.claude-plugin/plugin.json'))" \
  && "$PY" -c "import json; json.load(open('.claude-plugin/marketplace.json'))" \
  && "$PY" -c "import json; m=json.load(open('.claude-plugin/plugin.json')); assert 'name' in m, 'plugin.json missing required name field'; print('plugin name:', m['name'])" \
  || { echo "❌ validate-plugin failed"; fail=1; }

echo "── lint (ruff) — advisory unless CI_LOCAL_STRICT=1 ─────────"
if command -v ruff >/dev/null 2>&1; then
  if ! ruff check .; then
    if [ "${CI_LOCAL_STRICT:-0}" = "1" ]; then fail=1; else echo "⚠️  ruff findings (advisory, same as CI)"; fi
  fi
else
  echo "⚠️  ruff not installed — CI runs it (advisory); pip install ruff for parity"
fi

ran_any=0

run_pytest_leg() {
  py="$1"; label="$2"
  echo "── pytest ($label) ────────────────────────────────────────────"
  if ! command -v "$py" >/dev/null 2>&1; then
    echo "⏭️  SKIPPED — $label not installed here; the CI matrix covers this leg"
    return
  fi
  # An interpreter without pytest cannot say anything about the tests. That is a
  # missing leg, not a red one — reporting it as "pytest failed" makes an
  # environment gap indistinguishable from an actual test failure, which is the
  # one distinction this gate exists to make.
  if ! "$py" -c "import pytest" >/dev/null 2>&1; then
    echo "⏭️  SKIPPED — $label has no pytest; the CI matrix covers this leg"
    return
  fi
  if "$py" -m pytest tests/ -q; then
    ran_any=1
  else
    echo "❌ pytest failed on $label"
    fail=1
  fi
}

for py in python3.11 python3.12; do
  run_pytest_leg "$py" "$py"
done

# Fallback. On some setups the matrix names resolve to launcher shims with no
# packages while the interpreter that actually has the project installed is
# plain `python`. If that one reports a matrix version it is a legitimate leg —
# without this, the gate is unsatisfiable on such a machine and every push ends
# up waved through with the emergency bypass, which is worse than no gate.
if [ "$ran_any" = "0" ] && command -v python >/dev/null 2>&1; then
  ver="$(python -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || true)"
  case "$ver" in
    3.11|3.12) run_pytest_leg python "python $ver" ;;
    "") ;;
    *) echo "⏭️  python is $ver — outside the CI matrix, not counted as a leg" ;;
  esac
fi

if [ "$ran_any" = "0" ]; then
  echo "❌ no matrix interpreter available at all — install python3.11 or 3.12 (with pytest)"
  fail=1
fi

if [ "$fail" = "0" ]; then
  echo "✅ ci_local: all runnable checks green (parity with test.yml)"
else
  echo "❌ ci_local: failures above — CI would be red"
fi
exit $fail
