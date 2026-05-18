"""Parse a FIT file and extract laps + per-second records.

Usage:
    python3 coach/scripts/parse_fit.py --fit-path /tmp/garmin/activity.fit

Output: JSON with {"laps": [...], "records": [...]}
"""

from __future__ import annotations

import argparse
import json
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.fit_parser import parse_fit_laps, parse_fit_records


from app.utils.alerts import alert_on_failure


@alert_on_failure
def main() -> None:
    parser = argparse.ArgumentParser(description="Parse FIT file")
    parser.add_argument("--fit-path", required=True, help="Path to .fit file")
    args = parser.parse_args()

    fit_path = Path(args.fit_path)
    laps = parse_fit_laps(fit_path)
    records = parse_fit_records(fit_path)
    print(json.dumps({"laps": laps, "records": records}, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
