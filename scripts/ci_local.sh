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

echo "── validate-plugin ──────────────────────────────────────────"
python3 -c "import json; json.load(open('.claude-plugin/plugin.json'))" \
  && python3 -c "import json; json.load(open('.claude-plugin/marketplace.json'))" \
  && python3 -c "import json; m=json.load(open('.claude-plugin/plugin.json')); assert 'name' in m, 'plugin.json missing required name field'; print('plugin name:', m['name'])" \
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
for py in python3.11 python3.12; do
  echo "── pytest ($py) ────────────────────────────────────────────"
  if command -v "$py" >/dev/null 2>&1; then
    if "$py" -m pytest tests/ -q; then
      ran_any=1
    else
      echo "❌ pytest failed on $py"
      fail=1
    fi
  else
    echo "⏭️  SKIPPED — $py not installed here; the CI matrix covers this leg"
  fi
done
if [ "$ran_any" = "0" ]; then
  echo "❌ no matrix interpreter available at all — install python3.11 or 3.12"
  fail=1
fi

if [ "$fail" = "0" ]; then
  echo "✅ ci_local: all runnable checks green (parity with test.yml)"
else
  echo "❌ ci_local: failures above — CI would be red"
fi
exit $fail
