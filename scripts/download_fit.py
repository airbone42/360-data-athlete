"""Download FIT file from Garmin Connect for a given date.

Usage:
    python3 coach/scripts/download_fit.py --date YYYY-MM-DD

Output: JSON with {"fit_path": "/tmp/garmin/activity_YYYY-MM-DD.fit"}
"""

from __future__ import annotations

import argparse
import json
import sys
import os
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.garmin_client import download_fit_for_date


from app.utils.alerts import alert_on_failure


@alert_on_failure
def main() -> None:
    parser = argparse.ArgumentParser(description="Download FIT file from Garmin")
    parser.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args()

    fit_path = download_fit_for_date(args.date)
    print(json.dumps({"fit_path": str(fit_path)}))


if __name__ == "__main__":
    main()
