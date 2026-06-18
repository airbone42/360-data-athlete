"""HRV-Forecast für die nächste Nacht basierend auf personalisierter Load→HRV-Regression.

Nutzt das in `app/graphs/sub_athlete_context/context_builder.py` definierte Modell:
    expected_delta_pct = intercept + slope * daily_load

Output:
- Forecast-Wert (HRV-Erwartungswert für morgen früh)
- 68%-Konfidenzintervall (±1 res_std)
- Review-Trigger-Schwellen (±1.5 res_std)
- Modell-Koeffizienten + Datenbasis
- Letzte 10 Forecast-vs-Actual-Vergleiche

Usage:
    python3 scripts/hrv_forecast.py [--date YYYY-MM-DD] [--load X] [--json]

Defaults:
- Datum: heute
- Load: Summe aller bereits absolvierten Activities mit `icu_training_load` für das angegebene Datum
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.intervals_client import IntervalsClient
from app.graphs.sub_athlete_context.context_builder import (
    _build_hrv_sensitivity,
    _compute_hrv_responses,
    _slope_is_significant,
)
from app.utils.logging import configure

configure("hrv_forecast", level="WARNING")


async def _gather(target: date) -> tuple[list[dict], list[dict]]:
    # The load→HRV regression needs the FULL look-back window, so fetch it
    # from the live client — NOT the file cache. The per-day activity cache
    # only holds days that something already touched (typically the recent
    # weeks); cold-missing older days are not back-filled, which silently
    # starves the regression (e.g. 16 points from one month instead of the
    # ~90 available over 180 days). The cache stays the right tool for the
    # daily hot path; the forecast's regression window must be complete.
    client = IntervalsClient()
    oldest = (target - timedelta(days=180)).isoformat()
    newest = target.isoformat()
    acts = await client.get_activities(oldest=oldest, newest=newest)
    wellness = await client.get_wellness_history(oldest=oldest, newest=newest)
    return acts, wellness


def _baseline(wellness: list[dict]) -> float | None:
    recent = [w["hrv"] for w in wellness[-90:] if w.get("hrv") is not None]
    if not recent:
        return None
    return float(statistics.median(recent))


def _today_load(acts: list[dict], target: date) -> float:
    iso = target.isoformat()
    total = 0.0
    for a in acts:
        if (a.get("start_date_local") or "")[:10] != iso:
            continue
        total += a.get("icu_training_load") or 0
    return total


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=date.today().isoformat())
    ap.add_argument("--load", type=float, default=None,
                    help="Override load value (default: sum of today's activity loads).")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    target = date.fromisoformat(args.date)
    acts, wellness = asyncio.run(_gather(target))

    baseline = _baseline(wellness)
    if baseline is None:
        sys.stderr.write("No HRV history available.\n")
        return 1

    sensitivity = _build_hrv_sensitivity(acts, wellness, baseline)
    if sensitivity is None:
        sys.stderr.write("Insufficient data (need ≥10 load→hrv pairs).\n")
        return 2

    intercept, slope, res_std, slope_se = sensitivity
    load = args.load if args.load is not None else _today_load(acts, target)

    expected_pct = intercept + slope * load
    expected_hrv = baseline * (1 + expected_pct / 100)
    ci_lo = baseline * (1 + (expected_pct - res_std) / 100)
    ci_hi = baseline * (1 + (expected_pct + res_std) / 100)
    trigger_lo = baseline * (1 + (expected_pct - 1.5 * res_std) / 100)
    trigger_hi = baseline * (1 + (expected_pct + 1.5 * res_std) / 100)

    responses = _compute_hrv_responses(acts, wellness, baseline, sensitivity)
    recent_compare = []
    for d in sorted(responses.keys())[-10:]:
        r = responses[d]
        if "expected_pct" in r:
            recent_compare.append({
                "date": d,
                "actual_pct": r["pct"],
                "expected_pct": r["expected_pct"],
                "deviation": r["deviation"],
                "verdict": r["verdict"],
            })

    data_points = len([a for a in acts if (a.get("icu_training_load") or 0) > 0])
    if data_points < 20:
        data_quality = "insufficient"
    elif data_points < 40:
        data_quality = "limited"
    else:
        data_quality = "adequate"

    model_info: dict = {
        "intercept_pct": round(intercept, 3),
        "slope_pct_per_load": round(slope, 4),
        "residual_stddev_pct": round(res_std, 2),
        "data_points": data_points,
    }
    slope_significant = _slope_is_significant(slope, slope_se)
    model_info["slope_se"] = round(slope_se, 4) if slope_se != float("inf") else None
    model_info["slope_significant"] = slope_significant
    if slope > 0 and slope_significant:
        model_info["sanity_warning"] = (
            "Positive slope detected (load->HRV positiv korreliert) — "
            "bei intaktem Athlet ungewöhnlich; prüfe Daten auf Konfounder "
            "(Krankheit, Höhentraining, Pausen)"
        )

    out = {
        "target_date": target.isoformat(),
        "forecast_for": (target + timedelta(days=1)).isoformat(),
        "load": round(load, 1),
        "baseline_hrv": baseline,
        "data_quality": data_quality,
        "model": model_info,
        "forecast": {
            "expected_delta_pct": round(expected_pct, 1),
            "expected_hrv_ms": round(expected_hrv, 1),
            "ci68_lo": round(ci_lo, 1),
            "ci68_hi": round(ci_hi, 1),
            "review_trigger_lo": round(trigger_lo, 1),
            "review_trigger_hi": round(trigger_hi, 1),
            "verdict": (
                "uncertain" if data_quality == "insufficient"
                else "low_signal" if not slope_significant
                else None
            ),
        },
        "recent_compare": recent_compare,
    }
    # Remove None verdict to keep output clean when not overridden
    if out["forecast"]["verdict"] is None:
        del out["forecast"]["verdict"]

    if args.json:
        json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        f = out["forecast"]
        m = out["model"]
        print(f"Datenqualität: {data_quality} ({data_points} Datenpunkte)")
        if data_quality == "insufficient":
            print("  ⚠️  Zu wenig Daten (<20) — Forecast-Verdict: uncertain")
        elif not slope_significant:
            print("  ⚠️  Last→HRV-Slope nicht signifikant (95%-CI schließt 0 ein) — "
                  "Forecast-Verdict: low_signal (Last erklärt die HRV nicht)")
        print()
        print(f"HRV-Forecast für {out['forecast_for']} (basierend auf Load {out['load']} am {out['target_date']})")
        print()
        print(f"Erwartung:    {f['expected_hrv_ms']} ms ({f['expected_delta_pct']:+}% vs Baseline {out['baseline_hrv']})")
        print(f"68% CI:       {f['ci68_lo']} – {f['ci68_hi']} ms")
        print(f"Review wenn:  < {f['review_trigger_lo']} oder > {f['review_trigger_hi']} ms")
        print()
        print(f"Modell: ΔHRV% = {m['intercept_pct']} + {m['slope_pct_per_load']} × load")
        print(f"        residual σ = {m['residual_stddev_pct']}%, Datenpunkte = {m['data_points']}")
        if "sanity_warning" in m:
            print(f"\n⚠️  Sanity-Warnung: {m['sanity_warning']}")
        print()
        print("Letzte Forecast-vs-Actual-Vergleiche:")
        for c in recent_compare:
            sign = "+" if c["deviation"] >= 0 else ""
            print(f"  {c['date']}: actual {c['actual_pct']:+}% / expected {c['expected_pct']:+}% / dev {sign}{c['deviation']}% / {c['verdict']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
