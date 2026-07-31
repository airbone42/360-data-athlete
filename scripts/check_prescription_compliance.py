"""Report standing prescriptions that were not actually executed.

Tag-level due-warnings answer "did a core session happen?". They cannot see
a prescribed exercise that lives *inside* such a session — the block runs,
the tag is satisfied, and a dropped element leaves no trace. This script
closes that gap by comparing the `**Soll-Frequenz:**` declarations in
`exercise_progressions.md` against the exercises recorded in the muscle logs.

Usage:
    python3 scripts/check_prescription_compliance.py [--date YYYY-MM-DD] [--json]

Exit codes: 0 = clean, 1 = findings present, 2 = infrastructure error.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.analytics.prescription_compliance import (  # noqa: E402
    compute_prescription_compliance,
    format_findings,
)
from app.utils.config_loader import load_config  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date", default=date.today().isoformat())
    ap.add_argument("--lookback-days", type=int, default=60)
    ap.add_argument("--json", action="store_true", dest="as_json")
    args = ap.parse_args()

    try:
        today = date.fromisoformat(args.date)
    except ValueError:
        print(f"Invalid --date: {args.date}", file=sys.stderr)
        return 2

    try:
        progressions = load_config("exercise_progressions")
    except Exception as exc:  # noqa: BLE001
        print(f"Could not load exercise_progressions: {exc}", file=sys.stderr)
        return 2

    findings = compute_prescription_compliance(
        progressions, today, lookback_days=args.lookback_days
    )

    if args.as_json:
        print(json.dumps({"date": args.date, "findings": findings}, indent=2))
    else:
        text = format_findings(findings, lookback_days=args.lookback_days)
        print(text or "No prescription-compliance findings.")

    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
