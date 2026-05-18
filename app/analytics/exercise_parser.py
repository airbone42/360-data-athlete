"""Parser for exercise entries in intervals.icu activity descriptions.

Handles formats like:
  Wrist Curls: 3x15 je Seite, 6.5 kg — RPE 4
  L-Sit Tuck Hold: 3x25s RPE 8
  Farmer's Hold KB: 4 × 45s je Seite, 25 kg
  3x10 Push-ups RPE 6-7
  10 reps x 3 sets Goblet Squat 20kg

Unmatched lines are returned as-is for queue logging.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ParsedExercise:
    raw_line: str
    name: str | None
    sets: int | None
    reps: float | None
    duration_s: float | None
    weight_kg: float | None
    rpe: float | None
    per_side: bool
    load_mode_hint: str  # "timed" | "weighted" | "bodyweight" | "unknown"
    parse_ok: bool
    hold_s: float | None = None  # isometric hold-time within a rep (e.g. "3s Hold am Druckpunkt", "7s Hold")
    tempo: str | None = None  # tempo notation (e.g. "3-1-3", "3-1-1") if explicitly written


# ── Alias normalisation ─────────────────────────────────────────────────────

_ALIAS_NORMALISE: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bfarmer'?s?\s*hold\b", re.I), "farmer hold"),
    (re.compile(r"\bl-sit\s*tuck\s*hold\b", re.I), "l-sit tuck hold"),
    (re.compile(r"\bl-sit\s*parallettes?\b", re.I), "l-sit parallettes"),
    (re.compile(r"\bl-sit\b", re.I), "l-sit parallettes"),
    (re.compile(r"\bhollow\s*rock\b", re.I), "hollow rock"),
    (re.compile(r"\bhollow\s*hold\b", re.I), "hollow hold"),
    (re.compile(r"\bdead\s*bug\b", re.I), "dead bug"),
    (re.compile(r"\bpallof\s*press\b", re.I), "pallof press"),
    (re.compile(r"\bstir.the.pot\b", re.I), "stir the pot"),
    (re.compile(r"\bkb\s*horn\s*pinch\b", re.I), "kb horn pinch"),
    (re.compile(r"\bgrip\s*master\b", re.I), "gripmaster"),
    (re.compile(r"\bfinger.extensoren\s*band\b", re.I), "finger extensor band"),
    (re.compile(r"\bfinger.extensor\s*band\b", re.I), "finger extensor band"),
    (re.compile(r"\breverse\s*wrist\s*curl\b", re.I), "reverse wrist curl"),
    (re.compile(r"\bwrist\s*curl\b", re.I), "wrist curl"),
    (re.compile(r"\bhammer\s*curl\b", re.I), "hammer curl"),
    (re.compile(r"\breverse\s*curl\b", re.I), "reverse curl"),
    (re.compile(r"\bkurzhantel.curl\b", re.I), "kurzhantel curl"),
    (re.compile(r"\bbizeps.curl\b", re.I), "kurzhantel curl"),
    (re.compile(r"\bbulgarian\s*split\b", re.I), "bulgarian split squat"),
    (re.compile(r"\bsingle.leg\s*rdl\b", re.I), "single leg rdl"),
    (re.compile(r"\bsl-rdl\b", re.I), "single leg rdl"),
    (re.compile(r"\bhip\s*thrust\b", re.I), "hip thrust"),
    (re.compile(r"\bgoblet\s*squat\b", re.I), "goblet squat"),
    (re.compile(r"\bbox\s*jump\b", re.I), "box jump"),
    (re.compile(r"\btrx\s*row\b", re.I), "trx row"),
    (re.compile(r"\bsupinated\s*row\b", re.I), "supinated row"),
    (re.compile(r"\bkurzhantel.row\b", re.I), "kurzhantel row"),
    (re.compile(r"\blat.zug\b", re.I), "lat zug"),
    (re.compile(r"\bkb\s*overhead\s*press\b", re.I), "kb overhead press"),
    (re.compile(r"\boverhead\s*press\b", re.I), "kb overhead press"),
    (re.compile(r"\bdiagonal.?zug\b|\bdiagonal.pull\b", re.I), "diagonal pull"),
    (re.compile(r"\bpush.ups?\b|\bliegestütz\b", re.I), "push up"),
    (re.compile(r"\bplanche\s*lean\b", re.I), "planche lean"),
    (re.compile(r"\bdead\s*hang\b", re.I), "dead hang"),
    (re.compile(r"\bachilles\s*(exzentrik|reha)\b", re.I), "achilles exzentrik"),
    (re.compile(r"\bphysio.*(außenrotation|er)\b", re.I), "physio band er"),
    (re.compile(r"\bcalf\s*raise\b|\bwaden.heben\b|\bwadenheben\b", re.I), "calf raise"),
    (re.compile(r"\bside\s*plank\b|\bseitstütz\b", re.I), "side plank"),
    (re.compile(r"\bplank\b|\bunterarmstütz\b", re.I), "plank"),
]


def normalise_exercise_name(raw: str) -> str:
    """Apply alias normalisations to raw exercise name.

    Also strips trailing coaching-note markers (em-dash, en-dash, hyphen)
    that the upstream extractor sometimes includes as part of the name
    (e.g. "body-squat langsam —" → "body-squat langsam"). Without this,
    alias lookup fails for otherwise-mapped exercises.
    """
    name = raw.strip()
    # Strip trailing dash/em-dash separators that mark coaching notes
    # appended to the exercise name (e.g. "Hip-Hinge ohne Last — ...").
    # The character class covers em-dash, en-dash, hyphen-minus, and the
    # surrounding whitespace.
    name = re.sub(r"\s*[—–\-]\s*$", "", name)
    for pattern, replacement in _ALIAS_NORMALISE:
        name = pattern.sub(replacement, name)
    return name.strip().lower()


# ── Main parsing regex ───────────────────────────────────────────────────────

# Matches lines starting with "Name: N×M ..." or "N×M Name ..."
# Handles: 3x15, 3×15, 3 x 15, 3×45s, 3x25s, 10 reps x 3 sets, 4×45s
_LINE_RE = re.compile(
    r"""
    (?:
      (?P<name_pre>[A-ZÄÖÜ][^\n:—\-]{2,60}?)  # "Name:" prefix style
      \s*:\s*
    )?
    (?:
      (?:(?P<sets_a>\d+)\s*[x×*]\s*(?P<reps_a>\d+(?:\.\d+)?)(?P<unit_a>\s*s(?:ec)?|\s*min)?  # 3x15 | 3×45s
        |(?P<reps_b>\d+(?:\.\d+)?)\s*(?:reps?|wdh\.?)\s*[x×*]\s*(?P<sets_b>\d+)            # 10 reps x 3 sets
      )
    )
    (?:\s*(?:je\s*seite|per\s*side|/\s*seite|beidseitig))?  # optional per-side
    (?:\s*,\s*|\s+@?\s*)?
    (?:(?P<weight>\d+(?:\.\d+)?)\s*kg)?   # optional weight
    (?:[^/\n]{0,80}?                       # anything in between
     RPE\s*(?P<rpe>\d+(?:[,.\-–]\d+)?))?  # optional RPE or range
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Colon-prefix: extract everything before the first colon as exercise name.
# Allows hyphens (for names like "Stir-the-Pot", "Knee-to-Wall Dorsiflexion").
# Length limit 90 covers compound names like
# "Tandem stance + head rotation (gaze stabilization) on foam pad / yoga mat".
# ÄÖÜ keep the regex tolerant to German-spelled exercise names.
_NAME_COLON_RE = re.compile(
    r"^(?P<name>[A-ZÄÖÜ][^\n:]{2,90}?)\s*:",
    re.IGNORECASE,
)

_RPE_ONLY_RE = re.compile(r"RPE\s*(\d+(?:[,.\-–]\d+)?)", re.IGNORECASE)
_WEIGHT_ONLY_RE = re.compile(r"(\d+(?:\.\d+)?)\s*kg", re.IGNORECASE)
_PER_SIDE_RE = re.compile(r"je\s*seite|per\s*side|/\s*seite|beidseitig", re.IGNORECASE)
# Isometric hold-time within a rep — e.g. "3s Hold at the contact point", "7s Hold",
# "Hold 5s", "2 s Halt", "3-s-Hold". German "halten" / "halt" / "halte" remain in
# the pattern so notes written in German are still matched. Excludes the
# timed-duration case where the full rep IS the hold (those are captured as
# duration_s via the timed-unit branch of _LINE_RE).
_HOLD_RE = re.compile(
    r"(?:"
    r"(?P<a>\d+(?:[.,]\d+)?)\s*s(?:ek|ec)?\s*[-\s]?\s*(?:hold|hal[bt]|halten)\b"  # "3s Hold", "3 s halten"
    r"|"
    r"\b(?:hold|halten|halt|halte)\s+(?:für\s+|von\s+)?(?P<b>\d+(?:[.,]\d+)?)\s*s(?:ek|ec)?\b"  # "Hold 5s", "halten für 7s"
    r")",
    re.IGNORECASE,
)
# Tempo notation: "Tempo 3-1-1", "Tempo 3/1/3", "(3-1-3)" — eccentric/pause/concentric
_TEMPO_RE = re.compile(
    r"(?:tempo[\s:]*|^)\(?(\d)[\-/](\d)[\-/](\d)\)?",
    re.IGNORECASE,
)


def _parse_rpe(rpe_str: str | None) -> float | None:
    if not rpe_str:
        return None
    rpe_str = rpe_str.replace(",", ".").replace("–", "-")
    if "-" in rpe_str:
        parts = rpe_str.split("-")
        try:
            return (float(parts[0]) + float(parts[1])) / 2.0
        except ValueError:
            pass
    try:
        return float(rpe_str)
    except ValueError:
        return None


_SECTION_HEADER_RE = re.compile(
    r"^(?:"
    # Bilingual warm-up / cool-down / main-set / closing markers
    r"warm[\s\-]?up|cool[\s\-]?down|warmup|cooldown|"
    r"aufwärmen|abwärmen|hauptteil|main\s*(?:set|block)|"
    r"block\s+[\d\w]|"
    r"einleitung|introduction|abschluss|closing|"
    # Ninja / fitness block headers
    r"pull[\s\-]fokus|pull[\s\-]focus|push\s*\(|ninja(?:\s+core|\s+grip|\s*[–—]|\b(?!\s*\w+:))|"
    r"prävention|prevention|physio[\s\-]block|grip[\s\-](?:block|finisher)|"
    r"isometric\s+finisher|"
    r"achilles[\s\-]reha|achilles\s+reha|achilles[\s\-]rehab|"
    r"sprunggelenk[\s\-]mobilisation|ankle[\s\-]mobilisation|ankle[\s\-]mobilization|"
    r"massagepistole\s+wade|massage\s+gun\s+calf|"
    r"core\s+ninja|handgelenk[\s\-]konditionierung|wrist[\s\-]conditioning|"
    # ALL-CAPS bracketed/parenthesized block headers (German + English)
    r"core[\s\-]block|"
    r"balance[\s\-](?:block|hauptteil|main\s*set|fokus|focus)|"
    r"aktivierung\b|activation\b|indoor[\s\-]aktivierung|indoor[\s\-]activation|"
    r"mini[\s\-]wu\b|"
    r"hallen[\s\-]block|gym[\s\-]block|"
    r"dummy[\s\-]block|"
    r"hinweis(?:e)?\b|note(?:s)?\b|"
    r"phase[\s\-]?\d+[\s\-]block|"
    # Athlete-block-cycle headers (SHIFT A/B/C/D, BLOCK A/B/C, …) — these
    # are physio-block-rotation markers, not exercises.
    r"schicht\s+[a-d]\b|shift\s+[a-d]\b|block\s+[a-d]\b|"
    # Free-text constraint announcements (do not contain reps, never an
    # exercise entry).
    r"aktive\s+sperren\s+heute|aktive\s+sperren\b|active\s+blocks\s+today|active\s+blocks\b|"
    r"sperren\s+heute|blocks\s+today|"
    r"⛔|⚠️"
    r")",
    re.IGNORECASE,
)

# Coaching-prose / free-text lines — too long / too narrative / clearly not an
# exercise entry. These would otherwise spill into the unmapped queue as
# parser artefacts. Heuristics: ≥ 12 words AND prose-density (≥ 2 sentence
# terminators "." / "!" / "?" / "—" in mid-sentence). Also catches lines that
# start with markdown-style list markers "- " followed by prose. Sentence-start
# tokens are bilingual.
_COACHING_PROSE_RE = re.compile(
    r"(?:"
    # Lines starting with "- " (markdown list) + ≥ 10 alpha-words = prose
    r"^\s*[-•]\s+\S+(?:\s+\S+){9,}|"
    # Lines starting with a sentence-style verb conjugation common in coach notes
    r"^(?:heute\s+|gestern\s+|direkt\s+nach\s+|sehnen[\s\-]pflege|lauf[\s\-]wu|"
    r"today\s+|yesterday\s+|right\s+after\s+|tendon[\s\-]care|run[\s\-]wu)"
    r")",
    re.IGNORECASE,
)

# Suffixes that indicate the extracted "name" is actually parameter text, not
# an exercise name. Bilingual to support athletes writing in either language.
_PARAM_SUFFIX_WORDS = re.compile(
    r"\b("
    # German
    r"wdh|wiederholungen|beide\s*beine|beide\s*seiten|halten|sec\s*halten|"
    r"beidbeinig|gewichtsbelastet|langsam|einbeinig|schmerzfrei|phase\s*\d|"
    r"je\s*seite|beidseitig|fuß\s*frei|zehen|ferse|"
    # English
    r"reps|repetitions|both\s*legs|both\s*sides|hold|sec\s*hold|"
    r"bilateral|loaded|slow|unilateral|pain[\s-]?free|"
    r"per\s*side|toes|heel"
    r")\b",
    re.IGNORECASE,
)

# Exercises intentionally not tracked (no meaningful muscle-fatigue signal).
# Bilingual list to cover both German and English notes.
_SKIP_ALWAYS: frozenset[str] = frozenset({
    # German
    "sprunggelenk-kreisen", "sprunggelenk kreisen",
    "fußsohlen-kreisen am boden", "fußsohlen kreisen",
    "hüftbeuger-dehnung liegend",
    "aktive sprunggelenksmobilisation", "sprunggelenksmobilisation",
    # English
    "ankle circles",
    "foot-sole circles on the floor", "foot sole circles",
    "lying hip flexor stretch", "hip flexor stretch",
    "active ankle mobilisation", "active ankle mobilization", "ankle mobilisation",
})

# Stretch, mobilisation, and massage lines — not tracked for muscle fatigue
_STRETCH_MOBILITY_RE = re.compile(
    r"(?:"
    # Mobilisation/warmup routines (original _WARMUP_NOISE_RE patterns)
    r"\bschulterkreisen\b|\bhüftkreisen\b|\bknöchelkreisen\b|\bfingerstreckungen\b|"
    r"\bhandgelenk.rotationen\b|\barm.pendel\b|\bbeinpendel\b|"
    r"\barmkreisen\b|"
    r"\bhandgelenk[\s\-]mobil(?:isation|isierung)?\b|"
    r"\bwrist[\s\-]mobility\b|"
    r"\bmobilisieren\s+der\s+gelenke\b|\bsanftes\s+mobilisieren\b|\bgelenk.mobilisation\b|"
    # Stretches / Dehnung
    r"\bdehnung\b|\bdehnen\b|"
    r"\bstretch\b|"
    # Massage / Foam-rolling / faszien
    r"\bmassagepistole\b|"
    r"\bfoam[\s\-]roll(?:er|ing)?\b|\bfaszien[\s\-]?roll(?:en|er)?\b|"
    # Specific mobility exercises not worth tracking
    r"\bsprunggelenksmobilisation\b|"
    r"\bbauchatmung\b|"
    r"\bausschütteln\s+der\s+(?:hände|beine|arme|h)\b|"
    r"\b90\/90[\s\-]hip\b|"
    r"\bchild'?s\s+pose\b|"
    r"\bbws[\s\-]rotation\b|"
    r"\bbeckenkippen\s+liegend\b|"
    r"\bknie[\s\-]zur[\s\-]brust[\s\-]zug\b|"
    r"\bpiriformis[\s\-]dehnung\b|"
    r"\bhüftbeuger[\s\-]dehnung\b|"
    r"\bwaden[\s\-]dehnung\b|\bwade[\s\-]dehnen\b|"
    r"\bsoleus[\s\-]dehnung\b|"
    r"\bpec[\s\-]minor\s+stretch\b|"
    r"\bmuskelbauch\b|"
    # Yoga-/passive mobility poses (low-load, no muscle-fatigue signal)
    r"\bcat[\s\-]cow\b|\bkatze[\s\-]kuh\b|"
    r"\bpigeon\s+pose\b|\btaubenstellung\b|"
    r"\bcross[\s\-]body\s+schulterdehnung\b|"
    r"\btürrahmen[\s\-]brustdehnung\b|\bbrustöffner\b|"
    r"\btfl\b\s*\+?\s*\bquadrizeps?\b|"  # "Foam Roller TFL + Quadrizeps"
    r"\btfl[\s\-]?(?:roll|release|massage)\b"
    r")",
    re.IGNORECASE,
)

# Coaching instructions, pause notes, medical directions — not exercise entries
_INSTRUCTION_LINE_RE = re.compile(
    r"(?:"
    r"\bpause\s+zwischen\s+(?:sätzen|übungen)\b|"
    r"^\d+[\–\-]?\d*\s*s\s+pause\b|"            # "45s Pause", "60–75s Pause"
    r"\bstopp[\s\-]kriterium:|"
    r"\bstopp\s+bei\s+>|"
    r"\bleichtes\s+ziehen\s+ok\b|"
    r"\btherapeutischer\s+(?:block|reiz)\b|"
    r"\bpflichtblock\b|"
    r"\bnach\s+der\s+einheit\b|"
    r"\bathleten(?:feedback|präferenz):|"
    r"\bhrv\s*[-–]\d+%|"
    r"\bphase\s+\d+\s+aktiv\b|"
    r"\bkein\s+gripmaster\b|"
    r"\bscapula\s+aktiv\b|"
    r"^📹\s*filmtipp:|"
    r"^⚡|^🚨|^🔴|^🟡|^🟢|"
    r"\s*—>\s*feedback:|"                        # "Supinated Row —> Feedback: RPE 4"
    r"\bziehen\s+nach\s+.{1,15}normal\b|"
    r"\bauf\s+stufe.treppenstufe\b|"
    r"\btreppenstufe\s+wenn\s+möglich\b|"
    r"\bkein\s+(?:dips|overhead|gripmaster)\b|"
    r"—\s+\d+[x×]\s*\||"                        # "Hollow Hold — 3x | instructions"
    r"\bfokus\s+sprunggelenk"
    r")",
    re.IGNORECASE,
)


def parse_line(line: str) -> ParsedExercise | None:
    """Parse one description line into a ParsedExercise.

    Returns None if the line is clearly not an exercise entry (e.g. feedback annotations).
    """
    stripped = line.strip()
    if not stripped:
        return None
    # Skip feedback/coaching annotations
    if stripped.startswith("->") or stripped.startswith("→") or stripped.startswith("#"):
        return None
    # Skip section headers like "## Warm-up" or plain "WARM-UP (5 min)"
    if stripped.startswith("##") or stripped.startswith("**"):
        return None
    if _SECTION_HEADER_RE.match(stripped):
        return None

    m = _LINE_RE.search(stripped)
    if not m:
        return ParsedExercise(
            raw_line=stripped, name=None, sets=None, reps=None,
            duration_s=None, weight_kg=None, rpe=None,
            per_side=False, load_mode_hint="unknown", parse_ok=False,
        )

    # Extract sets/reps
    sets_raw = m.group("sets_a") or m.group("sets_b")
    reps_raw = m.group("reps_a") or m.group("reps_b")
    unit_raw = (m.group("unit_a") or "").strip().lower()

    sets_int: int | None = int(sets_raw) if sets_raw else None
    reps_float: float | None = float(reps_raw) if reps_raw else None

    # Heuristic: if sets > 20 and reps < 5, likely swapped
    if sets_int and reps_float and sets_int > 20 and reps_float < 5:
        sets_int, reps_float = int(reps_float), float(sets_int)

    # Duration vs reps
    duration_s: float | None = None
    reps_out: float | None = None
    is_timed = "s" in unit_raw or "sec" in unit_raw or "min" in unit_raw
    if is_timed and reps_float is not None:
        factor = 60.0 if "min" in unit_raw else 1.0
        duration_s = reps_float * factor
        reps_out = None
    else:
        reps_out = reps_float

    # Name — try colon-prefix first (handles hyphenated names like "Stir-the-Pot: 3x8").
    # Fall back to name_pre from main regex, then suffix extraction.
    colon_m = _NAME_COLON_RE.match(stripped)
    if colon_m:
        name_raw = colon_m.group("name")
    else:
        name_raw = m.group("name_pre") or _extract_name_from_line(stripped, m.start())
    name_normalised = normalise_exercise_name(name_raw) if name_raw else None

    # Weight
    weight_raw = m.group("weight")
    weight_kg: float | None = float(weight_raw) if weight_raw else None
    if weight_kg is None:
        wm = _WEIGHT_ONLY_RE.search(stripped)
        if wm:
            weight_kg = float(wm.group(1))

    # RPE
    rpe_raw = m.group("rpe")
    rpe = _parse_rpe(rpe_raw)
    if rpe is None:
        rm = _RPE_ONLY_RE.search(stripped)
        if rm:
            rpe = _parse_rpe(rm.group(1))

    # Per side
    per_side = bool(_PER_SIDE_RE.search(stripped))

    # Isometric Hold-time within a rep (separate from duration_s, which is the full-rep duration)
    hold_s: float | None = None
    hm = _HOLD_RE.search(stripped)
    if hm:
        hold_raw = hm.group("a") or hm.group("b")
        if hold_raw:
            try:
                hold_s = float(hold_raw.replace(",", "."))
            except ValueError:
                hold_s = None

    # Tempo notation (3-1-3 = eccentric-pause-concentric)
    tempo: str | None = None
    tm = _TEMPO_RE.search(stripped)
    if tm:
        tempo = f"{tm.group(1)}-{tm.group(2)}-{tm.group(3)}"
        # If no explicit Hold-token but tempo says 3-X-Y, treat the middle as hold-pause
        if hold_s is None and tm.group(2) != "0":
            try:
                hold_s = float(tm.group(2))
            except ValueError:
                pass

    # Load mode hint
    if is_timed:
        load_mode_hint = "timed"
    elif weight_kg:
        load_mode_hint = "weighted"
    else:
        load_mode_hint = "bodyweight"

    return ParsedExercise(
        raw_line=stripped,
        name=name_normalised,
        sets=sets_int,
        reps=reps_out,
        duration_s=duration_s,
        weight_kg=weight_kg,
        rpe=rpe,
        per_side=per_side,
        load_mode_hint=load_mode_hint,
        parse_ok=True,
        hold_s=hold_s,
        tempo=tempo,
    )


def _extract_name_from_line(line: str, match_start: int) -> str | None:
    """Try to find name from text before the matched sets/reps pattern."""
    prefix = line[:match_start].strip().rstrip(":-,")
    if len(prefix) >= 3:
        return prefix
    # Check after the sets/reps pattern for a trailing name
    suffix = line[match_start:].strip()
    # Remove the number pattern
    suffix = re.sub(r"^\d+\s*[x×*]\s*\d+(?:\.\d+)?\s*(?:s|sec|min)?\s*,?\s*", "", suffix, flags=re.I)
    suffix = re.sub(r"^\d+(?:\.\d+)?\s*kg\s*", "", suffix, flags=re.I)
    suffix = re.sub(r"RPE.*", "", suffix, flags=re.I).strip().rstrip("—-,")
    # Reject suffix if it reads like parameter text rather than an exercise name
    if len(suffix) >= 3 and not _PARAM_SUFFIX_WORDS.search(suffix):
        return suffix
    return None


def parse_description(description: str) -> tuple[list[ParsedExercise], list[str]]:
    """Parse full activity description into exercises + unmapped lines.

    Returns:
        parsed: list of successfully parsed exercises
        unmapped: raw lines that could not be parsed
    """
    parsed: list[ParsedExercise] = []
    unmapped: list[str] = []

    for line in description.splitlines():
        result = parse_line(line)
        if result is None:
            continue
        if result.parse_ok and result.name:
            if (result.name.lower() not in _SKIP_ALWAYS
                    and not _STRETCH_MOBILITY_RE.search(result.raw_line)):
                parsed.append(result)
        elif result.parse_ok is False and line.strip():
            # Only add to unmapped if it looks like it could be an exercise.
            # The strongest signal: presence of N×M-rep-counter. Real exercise
            # lines always carry a sets×reps pattern (`3×10`, `3x12`, `3×45s`).
            # Standalone duration markers (`30s`, `5 min`) appear in coaching
            # annotations and section headers ("MAIN – PULL (6 min)",
            # "Pause 60s zwischen Übungen", "GLUTE-RE-INTEGRATION (3 min)") —
            # those are not exercises and must NOT be queued as "(unresolved)".
            stripped = line.strip()
            has_rep_counter = bool(re.search(r"\d+\s*[x×]\s*\d", stripped))
            if not has_rep_counter:
                continue
            if (len(stripped) > 5
                    and not stripped.startswith("✅")
                    and not stripped.startswith(("•", "◦", "▪"))
                    and not stripped.startswith("Coaching")
                    and not _SECTION_HEADER_RE.match(stripped)
                    and not _STRETCH_MOBILITY_RE.search(stripped)
                    and not _INSTRUCTION_LINE_RE.search(stripped)
                    and not _COACHING_PROSE_RE.search(stripped)
                    # Prose lines: ≥ 10 words AND no x/× rep-counter — these
                    # are coaching notes / free narrative, never an exercise
                    # entry. Terminator-count is no longer required: long
                    # narrative without rep-counter is reliably prose
                    # regardless of dash usage.
                    and not (len(stripped.split()) >= 10
                             and not has_rep_counter)):
                unmapped.append(stripped)

    return parsed, unmapped


def match_to_mapping_key(exercise_name: str, exercise_mappings: dict) -> str | None:
    """Find mapping key for a normalised exercise name via alias lookup."""
    name = exercise_name.lower().strip()

    if name in exercise_mappings:
        return name

    # Exact alias match
    for key, mapping in exercise_mappings.items():
        if mapping.get("_type") == "endurance":
            continue
        aliases = [a.lower() for a in mapping.get("aliases", [])]
        if name in aliases:
            return key

    # Partial / substring match (longest alias wins)
    best_key: str | None = None
    best_len = 0
    for key, mapping in exercise_mappings.items():
        if mapping.get("_type") == "endurance":
            continue
        candidates = [a.lower() for a in mapping.get("aliases", [])] + [key]
        for candidate in candidates:
            # Check if all significant words of candidate appear in name or vice versa
            cwords = set(candidate.split())
            nwords = set(name.split())
            overlap = cwords & nwords
            if len(overlap) >= max(1, len(cwords) - 1) and len(candidate) > best_len:
                best_key = key
                best_len = len(candidate)

    return best_key
