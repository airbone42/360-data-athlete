"""HRV readiness classification — 7-day rolling ln-rMSSD vs a 60-day normal band.

Uses the classifier defined in `app/graphs/sub_athlete_context/context_builder.py`:
classify the 7-day rolling mean of ln-rMSSD against a 60-day reference band
(mean ± 0.5·SD of daily ln-rMSSD). Replaces the retired load→HRV regression
forecast (see framework/research/hrv-prediction-vs-readiness-modeling.md).

Output:
- Verdict (clear / above / watch / hold / insufficient_data) + consecutive
  days below band
- 7-day rolling mean and the normal band (ln + back-transformed ms)
- 60-day reference coverage + within-athlete CV
- Advisory day-to-day CV trend (rising / stable / falling)

Usage:
    python3 scripts/hrv_readiness.py [--date YYYY-MM-DD] [--json]

Defaults:
- Date: today
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.intervals_client import IntervalsClient
from app.graphs.sub_athlete_context.context_builder import _compute_hrv_readiness_band
from app.utils.logging import configure

configure("hrv_readiness", level="WARNING")

_VERDICT_EMOJI = {
    "hold": "🔴",
    "watch": "🟡",
    "clear": "🟢",
    "above": "🔵",
    "insufficient_data": "⚪",
}


async def _gather(target: date) -> list[dict]:
    # The classifier is wellness-only — no activity window needed. 90 days
    # covers the 60d reference band + the 7d rolling mean + the consecutive
    # walk-back (each walked-back day needs its own trailing 60d). Fetch from
    # the live client so the reference window is complete (the per-day cache
    # only holds recently-touched days).
    client = IntervalsClient()
    oldest = (target - timedelta(days=90)).isoformat()
    newest = target.isoformat()
    return await client.get_wellness_history(oldest=oldest, newest=newest)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=date.today().isoformat())
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    target = date.fromisoformat(args.date)
    wellness = asyncio.run(_gather(target))

    if not any(w.get("hrv") for w in wellness):
        sys.stderr.write("No HRV history available.\n")
        return 1

    readiness = _compute_hrv_readiness_band(wellness, target)
    out = {
        "target_date": target.isoformat(),
        "method": "7d-rolling ln-rMSSD vs 60d mean±0.5·SD band",
        **readiness,
    }

    if args.json:
        json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        verdict = out["verdict"]
        emoji = _VERDICT_EMOJI.get(verdict, "")
        cvt = out.get("cv_trend") or {}
        print(f"HRV-Readiness für {out['target_date']} ({out['method']})")
        print()
        if verdict == "insufficient_data":
            print(f"Verdict:      {emoji} insufficient_data "
                  f"({out['n_ref']} valide Tageswerte / 60d, <30 nötig)")
            print("              → Fallback auf 90d-Median+5%-Logik (intensityReadiness).")
        else:
            below = out["days_below"]
            suffix = f" (7d-Schnitt {below} Tag(e) unter Band)" if below else ""
            print(f"Verdict:      {emoji} {verdict}{suffix}")
            print(f"7d-Schnitt:   {out['rolling_mean_ms']} ms (ln {out['rolling_mean_ln']})")
            print(f"Normalband:   {out['band_low_ms']} – {out['band_high_ms']} ms "
                  f"(ln {out['band_low_ln']} – {out['band_high_ln']})")
            print(f"Referenz:     n={out['n_ref']} valide Tageswerte / 60d, CV {out['cv']}%")
        if cvt.get("trend") and cvt["trend"] != "insufficient_data":
            print(f"CV-Trend:     {cvt['trend']} (recent {cvt['cv_recent']}% vs "
                  f"prior {cvt['cv_prior']}%) — nur advisory")

    return 0


if __name__ == "__main__":
    sys.exit(main())
