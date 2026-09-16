"""Open progression steps, ordered, with per-chain collision detection.

Two failures share one cause, and the cause is that a pending step is filed
next to the exercise it belongs to and nowhere else.

**The counting failure.** Several exercises can come due in the same window,
and each one's entry says so in its own section. Nothing counts them together.
When two of them load the same tissue, running both steps in one session makes
the next morning's signal unattributable — the reading is spent and neither
step is confirmed. The collision is obvious once the steps are in one list and
invisible while they are in three files' worth of prose.

**The ordering failure.** When the order has already been decided — argued
once, agreed, written down — it is written into whichever exercise entry the
argument happened in. The next planning cycle reads the plan and the
constraints, not three exercise entries, so the order gets re-derived from
whatever heuristic is at hand. Re-deriving it is not neutral: a plausible
ordering (oldest queue entry first) can disagree with the decided one
(smallest distance to target band first), and then a settled decision has to
be argued a second time by the person who already won it.

This module makes both mechanical. An exercise entry declares its pending
step; the queue is assembled, grouped by chain, and surfaced in
`planningConstraints` as one block. Nothing here decides anything — it puts
the decision where the flow reads it.

Declaration (all three fields optional, `Schritt-offen` is what opts in):

    ### Wrist Curls
    - **Schritt-offen:** 11,5 → 12,5 kg
    - **Schritt-Kette:** Unterarm/Schulter
    - **Schritt-Rang:** 1

`Schritt-Kette` groups steps that load the same tissue, so the collision
warning fires per chain rather than across the whole file. `Schritt-Rang`
carries a decided order; entries without one sort after the ranked ones in
document order, which is the honest default — no rank means no decision, not
rank zero.

Fully opt-in: an exercise file with none of these fields produces no output,
so a fresh consumer sees nothing new.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# `### Exercise name` / `#### Exercise name` — same heading shape
# `prescription_compliance` keys off. Level is not meaningful, only the title.
_HEADING_RE = re.compile(r"^#{3,4}\s+(.+?)\s*$")


def _field_re(key: str) -> re.Pattern[str]:
    """Match `- **Key:** value` and `- Key: value`, bold or plain."""
    return re.compile(
        rf"\*\*{key}\s*:?\*\*\s*(.+?)\s*$" rf"|^\s*-?\s*{key}\s*:\s*(.+?)\s*$",
        re.IGNORECASE,
    )


_STEP_RE = _field_re("Schritt-offen")
_CHAIN_RE = _field_re("Schritt-Kette")
_RANK_RE = _field_re("Schritt-Rang")

UNASSIGNED_CHAIN = "ohne Kette"


@dataclass(frozen=True)
class OpenStep:
    """A progression step an exercise entry declares as pending."""

    exercise: str
    step: str
    chain: str
    rank: int | None
    order: int  # document position, the tiebreaker for unranked entries


def _value(match: re.Match[str]) -> str:
    """First non-empty group — the two alternatives of `_field_re`."""
    return next((g for g in match.groups() if g), "").strip()


def _strip_markup(text: str) -> str:
    """Drop bold markers so a value reads as plain text in the output."""
    return re.sub(r"\*\*|__", "", text).strip()


def parse_open_steps(content: str | None) -> list[OpenStep]:
    """Collect declared pending steps from an exercise-progressions file.

    Only entries carrying `Schritt-offen` are returned. A declaration outside
    any heading is ignored rather than attributed to a guessed exercise: a
    step booked against the wrong exercise is worse than an unlisted one,
    because it reads as deliberate.
    """
    if not content:
        return []

    steps: list[OpenStep] = []
    heading: str | None = None
    pending: dict[str, str] = {}

    def flush() -> None:
        nonlocal pending
        if heading and "step" in pending:
            rank_raw = pending.get("rank", "")
            rank_match = re.search(r"\d+", rank_raw)
            steps.append(
                OpenStep(
                    exercise=heading,
                    step=pending["step"],
                    chain=pending.get("chain") or UNASSIGNED_CHAIN,
                    rank=int(rank_match.group()) if rank_match else None,
                    order=len(steps),
                )
            )
        pending = {}

    for line in content.splitlines():
        if (m := _HEADING_RE.match(line)) is not None:
            flush()
            heading = _strip_markup(m.group(1))
            continue
        if heading is None:
            continue
        if (m := _STEP_RE.search(line)) is not None and "step" not in pending:
            pending["step"] = _strip_markup(_value(m))
            continue
        if (m := _CHAIN_RE.search(line)) is not None and "chain" not in pending:
            pending["chain"] = _strip_markup(_value(m))
            continue
        if (m := _RANK_RE.search(line)) is not None and "rank" not in pending:
            pending["rank"] = _strip_markup(_value(m))

    flush()
    return steps


def group_by_chain(steps: list[OpenStep]) -> dict[str, list[OpenStep]]:
    """Order each chain's steps: ranked first (ascending), then document order.

    An unranked step sorts last on purpose. It has no decided position, and
    silently promoting it in front of a step that does would hand the caller a
    made-up order wearing the same clothes as a decided one.
    """
    chains: dict[str, list[OpenStep]] = {}
    for step in steps:
        chains.setdefault(step.chain, []).append(step)
    for entries in chains.values():
        entries.sort(key=lambda s: (s.rank is None, s.rank or 0, s.order))
    return chains


def format_queue(steps: list[OpenStep]) -> str | None:
    """Render the queue for `planningConstraints`, or None when empty."""
    if not steps:
        return None

    chains = group_by_chain(steps)
    lines = ["🪜 Offene Progressionsschritte (declared in exercise_progressions.md):"]
    collision = False
    for chain, entries in sorted(chains.items()):
        if len(entries) > 1:
            collision = True
            lines.append(
                f"  ⚠️ Kette „{chain}“ — {len(entries)} Schritte offen, "
                "Reihenfolge wie deklariert:"
            )
        else:
            lines.append(f"  Kette „{chain}“ — 1 Schritt offen:")
        for pos, entry in enumerate(entries, start=1):
            marker = f"{pos}." if len(entries) > 1 else "  "
            rank_note = "" if entry.rank is not None else "  (kein Rang deklariert)"
            lines.append(f"    {marker} {entry.exercise} — {entry.step}{rank_note}")

    if collision:
        lines.append(
            "  → Zwei Schritte derselben Kette in einer Session machen die "
            "Folgetags-Ablesung unzuordenbar: ein Schritt pro Session. Die "
            "deklarierte Reihenfolge ist die entschiedene — nicht am Tag neu "
            "herleiten. Schneller wird die Schlange durch mehr Slots, nicht "
            "durch mehr Schritte pro Slot."
        )
    return "\n".join(lines)
