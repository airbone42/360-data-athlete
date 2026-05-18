"""Recovery rules and ninja-pillar definitions — canonical source for validator + context_builder."""
from __future__ import annotations
import re

# Bilingual leg-tag compat: the framework is migrating from the German tag
# "beine" to the English "legs". During the transition both forms are treated
# as synonyms — new plans emit "legs"; legacy data on intervals.icu still
# carries "beine". Any rule that wants to match leg-focused sessions can
# simply look for the canonical form ("legs"); activities tagged with the
# legacy form will still match thanks to `canonicalise_tags()` below.
# Retire this synonym set once historical data has migrated.
LEG_TAG_SYNONYMS: frozenset[str] = frozenset({"beine", "legs"})


def canonicalise_tags(raw_tags: list | None) -> list[str]:
    """Lowercase raw activity tags + apply bilingual leg-tag synonym expansion.

    If either "beine" or "legs" is present, both forms are added so any
    downstream tag check (using either string) matches uniformly. Returns
    a new list, never mutates the input.
    """
    tags = [str(t).lower() for t in (raw_tags or [])]
    if LEG_TAG_SYNONYMS & set(tags):
        merged = set(tags) | LEG_TAG_SYNONYMS
        return sorted(merged)
    return tags


# (tags_that_trigger, min_rest_days, label)
# Trigger tags use the new canonical English form ("legs") — the
# `canonicalise_tags()` helper at the read site ensures legacy
# "beine"-tagged activities still match.
RECOVERY_RULES: list[tuple[list[str], int, str]] = [
    (["plyo"], 3, "Plyo blocked"),
    (["legs"], 2, "Legs/strength blocked"),
    (["intervals"], 2, "Legs/Plyo blocked (post-interval)"),
    (["ninja", "upperbody"], 1, "Ninja upper body blocked"),
    (["ninja", "core"], 2, "Ninja core blocked (L-sit CNS recovery)"),
    # Grip → Pull-next-day is the physiological lock (forearm flexor → scapular
    # stabilisation during rowing). The tag system currently doesn't distinguish
    # between Pull and Push — both carry `upperbody`. Conservative: Push is
    # blocked along with Pull, even if not strictly required physiologically.
    # Granular separation possible via separate `pull`/`push` tags in a future
    # VALID_TAGS extension.
    (["ninja", "grip"], 2, "Ninja upper body blocked after Grip (forearm-flexor interference)"),
]

# Keyword-based overlap rules — checked against activity description text, not tags.
# rpe_tiers: dict keyed "low"/"mid"/"high" → (max_rpe_inclusive, hard_days, soft_days)
# hard_days: days where target RPE ≥6 of same group is blocked
# soft_days: additional days where only light dose (RPE ≤5) of same group is allowed
# default_tier: used when no RPE value found in matching line
MUSCLE_OVERLAP_RULES: list[dict] = [
    {
        "id": "wrist_flexors",
        "keywords": ["wrist curl", "reverse wrist curl"],
        "label": "Wrist flexor/extensor",
        "rpe_tiers": {
            "low": (5, 0, 0),   # RPE ≤5: no block (24h recovery sufficient)
            "mid": (7, 1, 0),   # RPE 6–7: 1-day hard block
            "high": (10, 2, 1), # RPE ≥8: 2 days hard, 1 day soft (tendon recovery)
        },
        "default_tier": "mid",
    },
    {
        "id": "grip_support",
        "keywords": ["farmer hold", "farmer's hold", "dead hold", "towel grip", "dead hang"],
        "label": "Grip support (forearm tendons)",
        "rpe_tiers": {
            "low": (5, 0, 0),
            "mid": (7, 1, 1),   # tendons recover more slowly → extra soft day
            "high": (10, 2, 1),
        },
        "default_tier": "mid",
    },
    {
        "id": "plyometrics",
        "keywords": ["box jump", "plyo push", "lunge jump", "clap push", "depth jump", "broad jump", "squat jump"],
        "label": "Plyometrics (CNS + tendons)",
        "rpe_tiers": {
            "low": (5, 1, 0),   # even light plyo needs 1 CNS recovery day (masters athlete)
            "mid": (7, 2, 1),
            "high": (10, 3, 1),
        },
        "default_tier": "mid",
    },
]


def _extract_rpe_from_line(line: str) -> float | None:
    """Extract first RPE value from a description line, e.g. 'RPE 6' or 'RPE 7-8' → 7.0."""
    m = re.search(r"RPE\s*(\d+)", line, re.IGNORECASE)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return None
    return None


NINJA_PILLAR_KEYWORDS: dict[str, list[str]] = {
    "Grip": ["gripmaster", "farmer's hold", "farmer's walk", "wrist curl", "finger-extensoren", "towel grip"],
    "Pull": ["trx row", "kurzhantel row", "supinated row", "zugseil row", "lat-zug", "rudern"],
    "Push": ["push-up", "pushup", "kneeling push", "dips", "trx push"],
    "Core": ["hollow rock", "hollow hold", "l-sit", "dead bug", "pallof press", "planche lean", "tuck hold"],
    "Explosive Power": ["clap push", "plyo push", "box jump", "explosive row"],
}

NINJA_TAG_TO_PILLAR: dict[str, list[str]] = {
    "grip": ["Grip"],
    "upperbody": ["Pull", "Push"],
    "core": ["Core"],
    "plyo": ["Explosive Power"],
}

# Backward-compatibility aliases — will be removed once all callers migrate
# to the new names. Currently re-exported so external scripts and tests can
# keep working during the rename transition.
NINJA_SAEULE_KEYWORDS = NINJA_PILLAR_KEYWORDS
NINJA_TAG_TO_SAEULE = NINJA_TAG_TO_PILLAR
