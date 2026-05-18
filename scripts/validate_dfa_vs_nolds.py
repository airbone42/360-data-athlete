#!/usr/bin/env python3
"""DFA-α1 Validierung: eigener Algorithmus vs. nolds.dfa Referenz.

Phase B des DFA-Zonen-Validierungs-Plans:
- Lädt `/tmp/rr_stufentest_20260422.txt` (heutiger Stufentest, 6820 Beats)
- Teilt in 7 Stufen à ~420s Polar-Zeit (nach Warm-up)
- Berechnet α1 pro Stufe mit:
    a) compute_dfa_alpha1() aus analyse_dfa_staged.py (unser Code)
    b) nolds.dfa(nvals=range(4,17)) als Literatur-Referenz
- Zusätzlich: synthetische Benchmarks (weißes Rauschen α≈0.5, 1/f α≈1.0,
  brown noise α≈1.5) durch beide Funktionen
- Output: Vergleichstabelle mit Diff, plus Labor-Anker IAS=128 bpm (2022)
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import nolds

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

from analyse_dfa_staged import (  # noqa: E402
    compute_dfa_alpha1,
    load_and_clean_polar_rr,
    _mean,
)
from app.utils.fit_parser import parse_fit_laps  # noqa: E402


# ---------------------------------------------------------------------------
# Synthetic benchmarks
# ---------------------------------------------------------------------------

def white_noise(n: int, seed: int = 42) -> list[float]:
    """α ≈ 0.5 (uncorrelated random signal)."""
    rng = np.random.default_rng(seed)
    return rng.standard_normal(n).tolist()


def pink_noise(n: int, seed: int = 42) -> list[float]:
    """1/f noise — α ≈ 1.0. Generated via Voss-McCartney approximation."""
    rng = np.random.default_rng(seed)
    num_rows = int(np.ceil(np.log2(n)))
    array = rng.standard_normal((num_rows, n))
    for row in range(num_rows):
        step = 2 ** row
        for col in range(0, n, step):
            array[row, col : col + step] = array[row, col]
    return array.sum(axis=0).tolist()


def brown_noise(n: int, seed: int = 42) -> list[float]:
    """Brownian motion (integrated white noise) — α ≈ 1.5."""
    rng = np.random.default_rng(seed)
    return np.cumsum(rng.standard_normal(n)).tolist()


def run_synthetic_benchmarks() -> list[dict]:
    """Run both algorithms on signals with known α values."""
    n = 2000  # enough beats for stable DFA-α1
    benchmarks = [
        ("white noise", white_noise(n), 0.5),
        ("1/f (pink) noise", pink_noise(n), 1.0),
        ("brown noise (integrated)", brown_noise(n), 1.5),
    ]
    results = []
    for name, signal, expected in benchmarks:
        ours = compute_dfa_alpha1(signal)
        ref = nolds.dfa(signal, nvals=list(range(4, 17)))
        results.append(
            {
                "name": name,
                "expected": expected,
                "ours": round(ours, 4) if ours is not None else None,
                "nolds": round(float(ref), 4),
                "diff_ours_vs_nolds": round(
                    abs(ours - float(ref)), 4
                ) if ours is not None else None,
                "ours_off_from_expected": round(
                    abs(ours - expected), 4
                ) if ours is not None else None,
                "nolds_off_from_expected": round(
                    abs(float(ref) - expected), 4
                ),
            }
        )
    return results


# ---------------------------------------------------------------------------
# Real data: split into stages and compare
# ---------------------------------------------------------------------------

def extract_stage_rr(
    cum_times: list[float],
    rr_values: list[float],
    warm_up_secs: float,
    stage_secs: float,
    num_stages: int,
    dfa_window_start: float,
    dfa_window_end: float,
) -> list[dict]:
    """Split RR stream into stages (Polar-time), return DFA-analysis windows."""
    stages = []
    for n in range(num_stages):
        stage_start = warm_up_secs + n * stage_secs
        win_start = stage_start + dfa_window_start
        win_end = stage_start + dfa_window_end
        window_rr = [
            rr for ct, rr in zip(cum_times, rr_values) if win_start <= ct < win_end
        ]
        stages.append(
            {
                "stage_num": n + 1,
                "polar_t_range": (win_start, win_end),
                "beats": len(window_rr),
                "hr_avg_bpm": round(_mean([60000.0 / rr for rr in window_rr]), 1)
                if window_rr else None,
                "rr_values": window_rr,
                "fit_lap_hr_avg": None,
                "fit_lap_hr_max": None,
            }
        )
    return stages


def extract_stages_from_fit(
    cum_times: list[float],
    rr_values: list[float],
    polar_start_epoch: float | None,
    fit_path: Path,
    garmin_start_epoch: float,
    skip_transition_secs: float,
    polar_local_tz_offset_secs: float = 0.0,
) -> tuple[list[dict], dict]:
    """Slice Polar RR using actual Garmin lap boundaries from FIT file.

    Skips first lap (warmup) and last lap (cooldown); treats middle laps as stages.
    Each stage's DFA window = [lap_start + skip_transition, lap_end] in Polar time.

    Args:
        polar_local_tz_offset_secs: seconds to ADD to polar_start_epoch to align
            with Garmin UTC. If Polar CSV stored local time as +00:00 (common
            with Polar Sensor Logger), pass the local UTC offset (e.g. 7200 for
            CEST). Default 0 assumes both epochs are true UTC.
    """
    fit_laps = parse_fit_laps(fit_path)
    if len(fit_laps) < 3:
        raise ValueError(f"FIT has only {len(fit_laps)} laps — need ≥3 (warmup + ≥1 stage + cooldown)")

    if polar_start_epoch is None:
        raise ValueError("Polar RR file has no phone timestamps — cannot align with FIT")

    # Polar's t=0 in Garmin's time frame:
    #   polar_in_garmin_t = (polar_start_epoch_true_utc) - garmin_start_epoch
    polar_true_utc = polar_start_epoch - polar_local_tz_offset_secs
    offset_polar_to_garmin = garmin_start_epoch - polar_true_utc
    # Positive offset → Polar started BEFORE Garmin by this many seconds
    # Convert: Garmin time T → Polar time (T + offset_polar_to_garmin)

    # Cumulative Garmin time per lap boundary
    lap_boundaries_garmin: list[tuple[float, float]] = []
    t_acc = 0.0
    for lap in fit_laps:
        dur = lap.get("duration_s") or 0
        lap_boundaries_garmin.append((t_acc, t_acc + dur))
        t_acc += dur

    # Stages = laps[1:-1] (skip warmup and cooldown)
    stages = []
    for idx, (g_start, g_end) in enumerate(lap_boundaries_garmin[1:-1], start=1):
        stage_num = idx  # 1-based stage number
        lap = fit_laps[idx]  # matches lap index in fit_laps (skipping [0] warmup)

        # Convert Garmin lap boundary → Polar-time
        p_start = g_start + offset_polar_to_garmin
        p_end = g_end + offset_polar_to_garmin

        # DFA window = [p_start + skip_transition, p_end]
        win_start = p_start + skip_transition_secs
        win_end = p_end

        window_rr = [
            rr for ct, rr in zip(cum_times, rr_values) if win_start <= ct < win_end
        ]
        hr_avg = (
            round(_mean([60000.0 / rr for rr in window_rr]), 1)
            if window_rr else None
        )

        stages.append(
            {
                "stage_num": stage_num,
                "polar_t_range": (round(win_start, 1), round(win_end, 1)),
                "beats": len(window_rr),
                "hr_avg_bpm": hr_avg,
                "rr_values": window_rr,
                "fit_lap_hr_avg": lap.get("avg_heart_rate"),
                "fit_lap_hr_max": lap.get("max_heart_rate"),
                "fit_lap_duration_s": lap.get("duration_s"),
            }
        )

    alignment_info = {
        "polar_start_epoch": polar_start_epoch,
        "polar_local_tz_offset_secs": polar_local_tz_offset_secs,
        "polar_true_utc_epoch": polar_true_utc,
        "garmin_start_epoch": garmin_start_epoch,
        "offset_polar_to_garmin": round(offset_polar_to_garmin, 2),
        "num_fit_laps": len(fit_laps),
        "num_stages_derived": len(stages),
        "skip_transition_secs": skip_transition_secs,
    }
    return stages, alignment_info


def read_garmin_start_from_fit(fit_path: Path) -> float:
    """Extract session start_time epoch (UTC) from FIT file."""
    import fitparse  # type: ignore
    ff = fitparse.FitFile(str(fit_path))
    for record in ff.get_messages("session"):
        for f in record:
            if f.name == "start_time" and f.value is not None:
                dt = f.value
                # fitparse returns naive datetime in UTC
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.timestamp()
    raise ValueError("No session start_time found in FIT file")


def compare_stages(stages: list[dict]) -> list[dict]:
    """Run both α1 algorithms on each stage window."""
    results = []
    for s in stages:
        rr = s["rr_values"]
        if len(rr) < 32:
            ours = None
            ref = None
        else:
            ours = compute_dfa_alpha1(rr)
            ref = float(nolds.dfa(rr, nvals=list(range(4, 17))))

        diff = None
        if ours is not None and ref is not None:
            diff = round(abs(ours - ref), 4)

        results.append(
            {
                "stage_num": s["stage_num"],
                "beats": s["beats"],
                "hr_avg_bpm": s["hr_avg_bpm"],
                "fit_lap_hr_avg": s.get("fit_lap_hr_avg"),
                "fit_lap_hr_max": s.get("fit_lap_hr_max"),
                "polar_t_range": s.get("polar_t_range"),
                "ours": round(ours, 4) if ours is not None else None,
                "nolds": round(ref, 4) if ref is not None else None,
                "diff": diff,
            }
        )
    return results


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def print_header(text: str) -> None:
    print("\n" + "=" * 78)
    print(text)
    print("=" * 78)


def format_stage_table(rows: list[dict]) -> str:
    lines = []
    has_fit = any(r.get("fit_lap_hr_avg") is not None for r in rows)
    if has_fit:
        lines.append(
            f"{'Stufe':<6} {'Beats':>6} {'HR_Polar':>9} {'HR_FIT':>7} {'ΔHR':>5} "
            f"{'α1_ours':>9} {'α1_nolds':>10} {'|Diff|':>8}"
        )
        lines.append("-" * 74)
        for r in rows:
            ours = f"{r['ours']:.4f}" if r["ours"] is not None else "  —   "
            ref = f"{r['nolds']:.4f}" if r["nolds"] is not None else "  —   "
            diff = f"{r['diff']:.4f}" if r["diff"] is not None else "  —   "
            hr_p = f"{r['hr_avg_bpm']:.1f}" if r["hr_avg_bpm"] is not None else "  —  "
            hr_f = f"{r['fit_lap_hr_avg']}" if r.get("fit_lap_hr_avg") is not None else "  — "
            if r.get("hr_avg_bpm") is not None and r.get("fit_lap_hr_avg") is not None:
                delta = r["hr_avg_bpm"] - r["fit_lap_hr_avg"]
                dhr = f"{delta:+.1f}"
            else:
                dhr = "  — "
            lines.append(
                f"{r['stage_num']:<6} {r['beats']:>6} {hr_p:>9} {hr_f:>7} {dhr:>5} "
                f"{ours:>9} {ref:>10} {diff:>8}"
            )
    else:
        lines.append(
            f"{'Stufe':<6} {'Beats':>6} {'HR ⌀':>7} {'α1_ours':>9} {'α1_nolds':>10} {'|Diff|':>8}"
        )
        lines.append("-" * 52)
        for r in rows:
            ours = f"{r['ours']:.4f}" if r["ours"] is not None else "  —   "
            ref = f"{r['nolds']:.4f}" if r["nolds"] is not None else "  —   "
            diff = f"{r['diff']:.4f}" if r["diff"] is not None else "  —   "
            hr = f"{r['hr_avg_bpm']:.1f}" if r["hr_avg_bpm"] is not None else "  —  "
            lines.append(
                f"{r['stage_num']:<6} {r['beats']:>6} {hr:>7} {ours:>9} {ref:>10} {diff:>8}"
            )
    return "\n".join(lines)


def format_benchmark_table(rows: list[dict]) -> str:
    lines = []
    lines.append(
        f"{'Signal':<26} {'α_expected':>11} {'α_ours':>9} {'α_nolds':>9} "
        f"{'|ours−nolds|':>13} {'|nolds−expected|':>16}"
    )
    lines.append("-" * 90)
    for r in rows:
        lines.append(
            f"{r['name']:<26} {r['expected']:>11.2f} "
            f"{r['ours']:>9.4f} {r['nolds']:>9.4f} "
            f"{r['diff_ours_vs_nolds']:>13.4f} {r['nolds_off_from_expected']:>16.4f}"
        )
    return "\n".join(lines)


def interpret_results(
    benchmark: list[dict],
    stage_results: list[dict],
    lab_vt1_bpm: int = 128,
) -> str:
    """Return textual interpretation of the validation outcome."""
    lines = []

    # 1. Does nolds pass the benchmark?
    max_nolds_off = max(r["nolds_off_from_expected"] for r in benchmark)
    nolds_valid = max_nolds_off < 0.15  # generous tolerance
    lines.append(
        f"Benchmark-Validität `nolds.dfa`: max |α_nolds − α_expected| = "
        f"{max_nolds_off:.4f} → {'OK' if nolds_valid else 'UNGENAU (Referenz fragwürdig!)'}"
    )

    # 2. Does our algorithm match nolds on synthetic + real?
    bench_diffs = [r["diff_ours_vs_nolds"] for r in benchmark if r["diff_ours_vs_nolds"] is not None]
    stage_diffs = [r["diff"] for r in stage_results if r["diff"] is not None]
    max_bench_diff = max(bench_diffs) if bench_diffs else 0.0
    max_stage_diff = max(stage_diffs) if stage_diffs else 0.0

    lines.append(
        f"Unser Algorithmus vs. nolds (synthetisch): max |Diff| = {max_bench_diff:.4f}"
    )
    lines.append(
        f"Unser Algorithmus vs. nolds (echt, Stufen): max |Diff| = {max_stage_diff:.4f}"
    )

    has_bug = max_bench_diff > 0.05 or max_stage_diff > 0.05
    lines.append(
        f"→ {'BUG WAHRSCHEINLICH' if has_bug else 'Algorithmen stimmen überein (Diff < 0.05)'}"
    )

    # 3. What does the method say about VT1, using nolds as reference?
    # DFA-α1 threshold 0.75 marks VT1. Find the HR where nolds crosses it.
    valid_rows = [r for r in stage_results if r["nolds"] is not None and r["hr_avg_bpm"] is not None]
    if len(valid_rows) >= 2:
        lines.append(
            f"\nα1-vs-HR nach nolds-Referenz (Laborwert IAS 2022 = {lab_vt1_bpm} bpm):"
        )
        for r in valid_rows:
            marker = ""
            if r["hr_avg_bpm"] >= lab_vt1_bpm - 5 and r["hr_avg_bpm"] <= lab_vt1_bpm + 5:
                marker = f"  ← Labor-IAS-Bereich ({lab_vt1_bpm}±5 bpm)"
            lines.append(
                f"  Stufe {r['stage_num']}: HR ⌀{r['hr_avg_bpm']:>5.1f} bpm → α1 = {r['nolds']:.3f}{marker}"
            )

        # Find the last stage where α1 > 0.75 (should be above VT1) and first where α1 < 0.75 (below VT1)
        # nolds-side
        above = [r for r in valid_rows if r["nolds"] > 0.75]
        below = [r for r in valid_rows if r["nolds"] < 0.75]
        if above and below:
            highest_above = max(above, key=lambda r: r["hr_avg_bpm"])
            lowest_below = min(below, key=lambda r: r["hr_avg_bpm"])
            if highest_above["hr_avg_bpm"] < lowest_below["hr_avg_bpm"]:
                # Linear interpolation to find α1=0.75 crossing in HR
                hr_hi, a_hi = highest_above["hr_avg_bpm"], highest_above["nolds"]
                hr_lo, a_lo = lowest_below["hr_avg_bpm"], lowest_below["nolds"]
                frac = (0.75 - a_hi) / (a_lo - a_hi) if a_lo != a_hi else 0.0
                vt1_interp = hr_hi + frac * (hr_lo - hr_hi)
                lines.append(
                    f"\nnolds-Schätzung VT1 (α1=0.75 Kreuzung, linear interpoliert): "
                    f"{vt1_interp:.1f} bpm"
                )
                diff_to_lab = vt1_interp - lab_vt1_bpm
                lines.append(
                    f"Abweichung zum 2022-Laborwert: {diff_to_lab:+.1f} bpm → "
                    f"{'innerhalb ±5 bpm (plausibel)' if abs(diff_to_lab) <= 5 else 'AUSSERHALB ±5 bpm (Methode unzuverlässig für diesen Athleten)'}"
                )
            else:
                lines.append("\nα1-Verlauf nicht monoton fallend — Methode fragwürdig für diese Daten.")
        else:
            lines.append(
                "\nα1 überschreitet/unterschreitet 0.75-Grenze nicht eindeutig — "
                "kein valider VT1-Schätzer ableitbar."
            )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Phase B: DFA-α1 Algorithmus-Validierung gegen nolds.dfa"
    )
    parser.add_argument(
        "--rr-file",
        type=str,
        default="/tmp/rr_stufentest_20260422.txt",
        help="Polar RR-Datei (default: heutige Stufentest-Datei)",
    )
    parser.add_argument("--warm-up-secs", type=int, default=596)
    parser.add_argument("--stage-secs", type=int, default=421)
    parser.add_argument("--num-stages", type=int, default=7)
    parser.add_argument(
        "--dfa-window-start",
        type=int,
        default=120,
        help="Start des DFA-Analyse-Fensters innerhalb der Stufe (s)",
    )
    parser.add_argument(
        "--dfa-window-end",
        type=int,
        default=421,
        help="Ende des DFA-Analyse-Fensters innerhalb der Stufe (s)",
    )
    parser.add_argument(
        "--lab-vt1-bpm",
        type=int,
        default=128,
        help="Labor-VT1-Anker (2022-Laktatdiagnostik IAS = 128 bpm)",
    )
    parser.add_argument(
        "--fit-path",
        type=str,
        default=None,
        help="FIT-Datei mit echten Garmin-Laps. Wenn gesetzt, werden Stage-Grenzen "
             "automatisch aus Laps abgeleitet (Warmup=Lap 1, Cooldown=letzter Lap, "
             "dazwischen = Stufen). Überschreibt --warm-up-secs/--stage-secs/--num-stages.",
    )
    parser.add_argument(
        "--polar-local-tz-offset-secs",
        type=int,
        default=7200,
        help="Sekunden-Offset der Polar-Zeitstempel zu echter UTC. Polar Sensor Logger "
             "stempelt oft Lokalzeit mit +00:00 — für CEST 7200 setzen. Default 7200.",
    )
    parser.add_argument(
        "--skip-transition-secs",
        type=int,
        default=120,
        help="Sekunden am Stufen-Anfang, die aus DFA ausgeschlossen werden (Transient).",
    )
    parser.add_argument(
        "--hr-sanity-tolerance-bpm",
        type=float,
        default=2.0,
        help="Max. |Polar-HR − FIT-Lap-HR| im Fenster. Bei Überschreitung Warnung.",
    )
    args = parser.parse_args()

    rr_path = Path(args.rr_file)
    if not rr_path.exists():
        print(f"FEHLER: RR-Datei nicht gefunden: {rr_path}", file=sys.stderr)
        return 1

    # --- Synthetic benchmarks ---
    print_header("Synthetische Benchmarks (bekannte α-Werte)")
    bench_results = run_synthetic_benchmarks()
    print(format_benchmark_table(bench_results))

    # --- Real-data stage comparison ---
    print_header(f"Echte Daten: {rr_path.name}")
    cum_times, rr_values, stats, polar_start_epoch = load_and_clean_polar_rr(rr_path)
    print(
        f"Beats roh: {stats['raw_beats']} | valide: {stats['valid_beats']} "
        f"({100 * stats['valid_beats'] / max(stats['raw_beats'], 1):.1f}%)"
    )
    print(
        f"Polar-Zeitspanne: {cum_times[-1]:.1f}s "
        f"({cum_times[-1] / 60:.1f} min)"
    )

    if args.fit_path:
        fit_path = Path(args.fit_path)
        if not fit_path.exists():
            print(f"FEHLER: FIT-Datei nicht gefunden: {fit_path}", file=sys.stderr)
            return 1
        garmin_start_epoch = read_garmin_start_from_fit(fit_path)
        print(
            f"Garmin Activity Start (UTC): "
            f"{datetime.fromtimestamp(garmin_start_epoch, timezone.utc).isoformat()}"
        )
        stages, alignment = extract_stages_from_fit(
            cum_times, rr_values, polar_start_epoch,
            fit_path, garmin_start_epoch,
            skip_transition_secs=args.skip_transition_secs,
            polar_local_tz_offset_secs=args.polar_local_tz_offset_secs,
        )
        print(
            f"Polar→Garmin Offset: {alignment['offset_polar_to_garmin']:+.2f}s "
            f"(Polar startete {'vor' if alignment['offset_polar_to_garmin'] > 0 else 'nach'} Garmin)"
        )
        print(f"FIT-Laps: {alignment['num_fit_laps']} → Stufen (ohne Warmup/Cooldown): {alignment['num_stages_derived']}")
    else:
        stages = extract_stage_rr(
            cum_times, rr_values,
            args.warm_up_secs, args.stage_secs, args.num_stages,
            args.dfa_window_start, args.dfa_window_end,
        )

    stage_results = compare_stages(stages)
    print()
    print(format_stage_table(stage_results))

    # --- HR-Sanity-Gate (nur wenn FIT vorhanden) ---
    sanity_warnings = []
    if args.fit_path:
        for r in stage_results:
            p = r.get("hr_avg_bpm")
            f = r.get("fit_lap_hr_avg")
            if p is not None and f is not None:
                if abs(p - f) > args.hr_sanity_tolerance_bpm:
                    sanity_warnings.append(
                        f"Stufe {r['stage_num']}: ΔHR = {p - f:+.1f} bpm "
                        f"(Polar {p:.1f} vs FIT {f}) — Alignment verdächtig"
                    )
        if sanity_warnings:
            print_header("⚠️ HR-SANITY WARNUNG")
            for w in sanity_warnings:
                print(f"  {w}")
        else:
            print(f"\n✅ HR-Sanity OK (alle Stufen innerhalb ±{args.hr_sanity_tolerance_bpm} bpm)")

    # --- Interpretation ---
    print_header("Interpretation")
    print(interpret_results(bench_results, stage_results, lab_vt1_bpm=args.lab_vt1_bpm))

    return 0


if __name__ == "__main__":
    sys.exit(main())
