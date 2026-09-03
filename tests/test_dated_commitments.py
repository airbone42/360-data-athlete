"""Tests for the near-term dated-commitment scan.

The scan exists because a scheduling decision filed outside the slot ledger is
invisible to the planning flow. The interesting cases are therefore about
precision, not recall: these config files are dense with historical dates, and
a scan that surfaces them all is one the planner learns to ignore.
"""

from datetime import date

import pytest

from app.analytics.dated_commitments import find_dated_commitments, format_commitments

TODAY = date(2026, 9, 3)


def _texts(**kwargs: str) -> dict[str, str]:
    return {f"{name}.md": text for name, text in kwargs.items()}


class TestFindDatedCommitments:
    def test_finds_forward_dated_line(self):
        sources = _texts(
            exercise_progressions=(
                "- **Achilles-Rückmeldung am Fr 04.09. morgens einmalig abfragen** "
                "— erste schwere Wadenlast seit der Reha."
            )
        )
        findings = find_dated_commitments(sources, TODAY)

        assert len(findings) == 1
        assert findings[0]["file"] == "exercise_progressions.md"
        assert findings[0]["line"] == 1
        assert findings[0]["dates"] == [date(2026, 9, 4)]

    def test_today_itself_counts(self):
        sources = _texts(athlete_static="Erst-Ausführung 03.09.2026 im Bein-Block.")
        assert find_dated_commitments(sources, TODAY)

    def test_ignores_dates_before_today(self):
        """The whole file is history; only the horizon makes the scan usable."""
        sources = _texts(
            exercise_progressions=(
                "- Anker gesetzt am 13.05.2026, bestätigt 22.07.2026, "
                "Video-Befund 11.06.2026 sauber."
            )
        )
        assert find_dated_commitments(sources, TODAY) == []

    def test_ignores_dates_beyond_horizon(self):
        sources = _texts(competition_notes="Generalprobe steht am 04.10.2026 an.")
        assert find_dated_commitments(sources, TODAY, horizon_days=7) == []

    def test_horizon_is_inclusive_at_both_ends(self):
        sources = _texts(
            a="Slot am 03.09.2026.",
            b="Slot am 10.09.2026.",
            c="Slot am 11.09.2026.",
        )
        files = {f["file"] for f in find_dated_commitments(sources, TODAY, horizon_days=7)}
        assert files == {"a.md", "b.md"}

    @pytest.mark.parametrize(
        "line",
        [
            "✅ Ausführung 04.09.2026: 3×10 gelaufen, RPE 6.",
            "~~Slot 05.09.~~ erledigt",
            "Der Block war am 04.09. Teil des Kurstrainings.",
            "Session 05.09.2026 absolviert, keine Auffälligkeit.",
        ],
    )
    def test_skips_retrospective_lines(self, line):
        """A line reporting a past execution is documentation, not a commitment."""
        assert find_dated_commitments(_texts(exercise_log=line), TODAY) == []

    def test_bare_day_month_resolves_into_current_year(self):
        sources = _texts(athlete_static="Nächster Heim-Slot 06.09., danach Kadenz +2 Tage.")
        findings = find_dated_commitments(sources, TODAY)
        assert findings[0]["dates"] == [date(2026, 9, 6)]

    def test_bare_day_month_rolls_into_next_year_across_new_year(self):
        """A bare `05.01.` written in December means the coming January."""
        sources = _texts(athlete_static="Wiedervorlage 05.01.")
        findings = find_dated_commitments(sources, date(2026, 12, 28), horizon_days=14)
        assert findings[0]["dates"] == [date(2027, 1, 5)]

    def test_explicit_past_year_is_not_rolled_forward(self):
        """`04.09.2025` is history even though the day/month sit in the window."""
        sources = _texts(athlete_static="Befund vom 04.09.2025 dokumentiert hier.")
        assert find_dated_commitments(sources, TODAY) == []

    def test_ignores_impossible_dates(self):
        sources = _texts(athlete_static="Verhältnis 32.13. ist kein Datum, nur Prosa.")
        assert find_dated_commitments(sources, TODAY) == []

    @pytest.mark.parametrize(
        "line",
        [
            "Stir-the-Pot: 3×8 je Richtung, Tempo 3-0-3, RPE 6",
            "McGill Curl-up: Pyramide 6/4/2 je Seite @ 10s Hold",
            "Wadenheben schwer: 3x10/Seite @ +8 kg",
        ],
    )
    def test_set_rep_notation_is_not_a_date(self, line):
        assert find_dated_commitments(_texts(exercise_progressions=line), TODAY) == []

    def test_multiple_dates_on_one_line_are_deduped_and_sorted(self):
        sources = _texts(plan="Bein-Tag 03.09., Long Run 06.09., Nachkontrolle 06.09.")
        findings = find_dated_commitments(sources, TODAY)
        assert findings[0]["dates"] == [date(2026, 9, 3), date(2026, 9, 6)]

    def test_results_are_ordered_by_earliest_date(self):
        sources = _texts(
            b_file="Termin 06.09.2026 steht.",
            a_file="Termin 04.09.2026 steht.",
        )
        findings = find_dated_commitments(sources, TODAY)
        assert [f["file"] for f in findings] == ["a_file.md", "b_file.md"]

    def test_empty_and_short_lines_are_skipped(self):
        sources = _texts(athlete_static="\n\n04.09.\n\nrichtige Zusage am 04.09.2026 hier\n")
        findings = find_dated_commitments(sources, TODAY)
        assert len(findings) == 1
        assert findings[0]["line"] == 5

    def test_empty_sources_yield_nothing(self):
        assert find_dated_commitments({}, TODAY) == []
        assert find_dated_commitments({"empty.md": ""}, TODAY) == []


class TestFormatCommitments:
    def test_returns_none_without_findings(self):
        assert format_commitments([]) is None

    def test_block_names_the_canonical_location(self):
        findings = find_dated_commitments(
            _texts(exercise_progressions="Erst-Ausführung am 04.09.2026 im Bein-Block."),
            TODAY,
        )
        out = format_commitments(findings)

        assert "competition_plan.md" in out
        assert "Slot-Buchführung" in out
        assert "exercise_progressions.md:1" in out
        assert "2026-09-04" in out

    def test_long_snippets_are_truncated(self):
        findings = find_dated_commitments(
            _texts(athlete_static="Slot 04.09.2026 " + "Begründungsprosa " * 40), TODAY
        )
        out = format_commitments(findings, snippet_chars=60)

        body = [ln for ln in out.splitlines() if ln.startswith("  - ")][0]
        assert "…" in body
        assert len(body) < 140

    def test_overflow_is_counted_not_dropped_silently(self):
        sources = {f"f{i}.md": "Termin 04.09.2026 hier" for i in range(12)}
        out = format_commitments(find_dated_commitments(sources, TODAY), max_lines=3)

        assert len([ln for ln in out.splitlines() if ln.startswith("  - f")]) == 3
        assert "9 weitere" in out

    def test_phrasing_asks_for_reconciliation_not_obedience(self):
        """The entry may be the stale side — the planner has to reconcile."""
        findings = find_dated_commitments(
            _texts(athlete_static="Long Run am 06.09.2026."), TODAY
        )
        out = format_commitments(findings)

        assert "prüfen" in out
        assert "nachgetragen" in out
