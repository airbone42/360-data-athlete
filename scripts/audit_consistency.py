"""Consistency scanner for the coach knowledge base.

Mechanical drift checks between `config/`, `.claude/agents/`, `prompts/`,
`exercise_muscle_mapping.json` and external sources (intervals.icu, Strava).

Output: JSON to stdout — consumed by the config-auditor agent.

Usage:
    python3 scripts/audit_consistency.py                  # online, JSON
    python3 scripts/audit_consistency.py --offline        # local files only
    python3 scripts/audit_consistency.py --human          # readable summary
    python3 scripts/audit_consistency.py --check ORPHAN   # single check
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from app.utils.paths import (  # noqa: E402
    CONFIG_DIR,
    CONFIG_FALLBACK,
    COACH_HOME,
    DATA_DIR,
    FRAMEWORK_ROOT,
    resolve_config,
)

logger = logging.getLogger("audit_consistency")

HIGH, MEDIUM, LOW = "HIGH", "MEDIUM", "LOW"

# Trigger phrases in NOTEs indicating healing / recovery resolution.
# Phrases (not single words) to avoid false positives like "weg" → "wegen".
HEALING_KEYWORDS = [
    "schmerzfrei",
    "ausgeheilt",
    "beschwerdefrei",
    "geht wieder",
    "wieder fit",
    "kein schmerz",
    "keine schmerzen",
    "kein ziehen",
    "kein problem",
    "schmerz weg",
    "schmerzen weg",
    "ziehen weg",
    "geheilt",
    "wieder ok",
]

# Statische Restriction-Strings, die in Agenten/Prompts als Hardcode auftreten
RESTRICTION_PATTERNS: dict[str, list[str]] = {
    "schulter_overhead": [
        r"overhead.{0,10}restriction",
        r"kein\s+overhead",
        r"overhead\s+verboten",
        r"overhead\s+gesperrt",
    ],
    "schulter_push": [
        r"push\s+verboten",
        r"keine?\s+push.?ups?",
        r"keine?\s+brust",
    ],
    "schulter_pull": [
        r"pull\s+eingeschr",
        r"kein\s+pull.?up",
        r"kein\s+hang",
        r"dead\s+hang.+gesperrt",
    ],
    "achilles": [
        r"achilles.+gereizt",
        r"achilles.+gesperrt",
        r"achilles.+phase\s*[12]",
        r"keine?\s+intervalle.+achilles",
        r"explosive\s+power.+gesperrt.+achilles",
    ],
    "it_band": [
        r"it.?band.+gesperrt",
        r"kein\s+bergab",
    ],
}

# Files scanned for hardcoded values
HARDCODE_SCAN_GLOBS = [
    ".claude/agents/*.md",
    "prompts/*.yaml",
    "config/equipment.md",
]

# Files excluded from hardcode scan (meta-files about the audit itself)
HARDCODE_SCAN_EXCLUDE = {
    ".claude/agents/config-auditor.md",
    ".claude/agents/config-fixer.md",
}


# ── Helpers ──────────────────────────────────────────────────────────


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _finding(
    severity: str,
    category: str,
    source_file: str,
    *,
    source_line: int | None = None,
    evidence: str = "",
    canonical_source: str | None = None,
    suggested_action: str = "review",
    fix_hint: str = "",
    description: str = "",
) -> dict[str, Any]:
    return {
        "severity": severity,
        "category": category,
        "source_file": source_file,
        "source_line": source_line,
        "evidence": evidence,
        "canonical_source": canonical_source,
        "suggested_action": suggested_action,
        "fix_hint": fix_hint,
        "description": description,
    }


def _parse_risk_zones() -> list[dict[str, str]]:
    """Parse Risikozonen-Tabelle aus athlete_static.md."""
    text = _read(resolve_config("athlete_static.md"))
    m = re.search(
        r"## Risikozonen.*?\n\| Zone \|.+?\n((?:\|.+\n)+)",
        text,
        re.DOTALL,
    )
    if not m:
        return []
    rows = m.group(1).strip().splitlines()
    zones: list[dict[str, str]] = []
    for row in rows:
        if row.startswith("|---") or row.startswith("| ---"):
            continue
        cells = [c.strip() for c in row.split("|")[1:-1]]
        if len(cells) < 4:
            continue
        zones.append({
            "zone": cells[0].strip("* "),
            "status": cells[1],
            "warnings": cells[2],
            "action": cells[3],
        })
    return zones


# ── Check 1: HR-Zonen ────────────────────────────────────────────────


def check_hr_zones(athlete_settings: dict | None) -> list[dict]:
    if not athlete_settings:
        return []
    icu_zones = athlete_settings.get("hr_zones") or []
    if not icu_zones:
        # API returns no zone field — no comparison possible, no drift finding
        return []
    text = _read(resolve_config("athlete_status.md"))
    m = re.search(r"hr_zones:\s*\[([0-9,\s]+)\]", text)
    if not m:
        return []
    declared = [int(x.strip()) for x in m.group(1).split(",") if x.strip()]
    if list(declared) != list(icu_zones):
        line = text[: m.start()].count("\n") + 1
        return [_finding(
            HIGH,
            "hr_zones_drift",
            "config/athlete_status.md",
            source_line=line,
            evidence=f"deklariert={declared} | intervals.icu={list(icu_zones)}",
            canonical_source="intervals.icu athlete_settings.hr_zones",
            suggested_action="update_status_md",
            fix_hint="HR-Zonen-Liste in athlete_status.md auf intervals.icu-Werte aktualisieren",
            description="HR-Zonen in athlete_status.md weichen von intervals.icu ab — Spezialisten arbeiten ggf. mit falschen Schwellwerten",
        )]
    return []


# ── Check 2: Orphan Muscle IDs ───────────────────────────────────────


def check_orphan_muscles() -> list[dict]:
    db_text = _read(resolve_config("muscle_db.md"))
    valid_ids: set[str] = set()
    for line in db_text.splitlines():
        m = re.match(r"\|\s*([a-z][a-z0-9_]+)\s*\|", line)
        if m:
            valid_ids.add(m.group(1))

    mapping_path = resolve_config("exercise_muscle_mapping.json")
    try:
        mapping = json.loads(_read(mapping_path))
    except json.JSONDecodeError as e:
        return [_finding(
            HIGH, "json_parse_error", "config/exercise_muscle_mapping.json",
            evidence=str(e),
            description="JSON ist nicht parsebar — Mapping-Konsumenten brechen",
        )]

    findings: list[dict] = []
    for ex_key, ex in mapping.items():
        if ex_key.startswith("_"):
            continue
        for role in ("primary", "secondary", "stabilizer"):
            for entry in ex.get(role, []) or []:
                muscle_id = entry.get("muscle")
                if muscle_id and muscle_id not in valid_ids:
                    findings.append(_finding(
                        MEDIUM,
                        "orphan_muscle_id",
                        "config/exercise_muscle_mapping.json",
                        evidence=f"{ex_key}.{role}: '{muscle_id}'",
                        canonical_source="config/muscle_db.md",
                        suggested_action="add_or_rename",
                        fix_hint=f"Add muscle ID '{muscle_id}' to muscle_db.md or fix the mapping entry",
                        description=f"Exercise '{ex_key}' ({role}) references non-existent muscle ID '{muscle_id}'",
                    ))
    return findings


# ── Check 3: Unmapped Exercises ──────────────────────────────────────


def check_unmapped_exercises() -> list[dict]:
    path = DATA_DIR / "muscles" / "_unmapped.jsonl"
    if not path.exists():
        return []
    findings: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        findings.append(_finding(
            LOW,
            "unmapped_exercise",
            "data/muscles/_unmapped.jsonl",
            evidence=f"{entry.get('parsed_name')} (act {entry.get('activity_id')}, {entry.get('date')})",
            canonical_source="config/exercise_muscle_mapping.json",
            suggested_action="add_mapping",
            fix_hint=f"Add mapping for '{entry.get('parsed_name')}' in exercise_muscle_mapping.json",
            description=f"Exercise in activity {entry.get('activity_id')} could not be mapped — muscle load missing from DB",
        ))
    return findings


# ── Check 4: NOTE-vs-Static Drift ────────────────────────────────────


def check_note_vs_static(notes: list[dict] | None) -> list[dict]:
    if not notes:
        return []
    zones = _parse_risk_zones()
    if not zones:
        return []

    findings: list[dict] = []
    for zone in zones:
        zone_name = zone["zone"]
        status = zone["status"]
        # Only check "aktiv eingeschränkt" or "Phase X aktiv" statuses
        if not re.search(r"aktiv|phase", status, re.IGNORECASE):
            continue
        # Search for healing indicators in NOTEs for this zone
        zone_keywords = _zone_keywords(zone_name)
        matches: list[str] = []
        for note in notes:
            body = (note.get("description") or note.get("name") or "").lower()
            if not body:
                continue
            if not any(k.lower() in body for k in zone_keywords):
                continue
            for healing in HEALING_KEYWORDS:
                if healing in body:
                    date_str = (note.get("start_date_local") or note.get("start_date") or "")[:10]
                    snippet = body[max(0, body.find(healing) - 40): body.find(healing) + 40]
                    matches.append(f"{date_str}: …{snippet}…")
                    break
        if matches:
            findings.append(_finding(
                MEDIUM,
                "note_vs_static_drift",
                "config/athlete_static.md",
                evidence=f"Zone '{zone_name}' (status: {status}) — healing indicators in NOTEs:\n  - "
                         + "\n  - ".join(matches[:5]),
                canonical_source="intervals.icu NOTEs (4w)",
                suggested_action="review_zone_status",
                fix_hint=f"Review status of '{zone_name}' — consider setting to 'latent' or 'resolved'",
                description=f"Risk zone '{zone_name}' is set to '{status}', but NOTEs contain healing indicators",
            ))
    return findings


def _zone_keywords(zone_name: str) -> list[str]:
    base = zone_name.lower()
    keywords = [base]
    if "schulter" in base:
        keywords.extend(["schulter", "shoulder", "overhead"])
    if "achilles" in base:
        keywords.extend(["achilles", "achillessehne", "wade"])
    if "it-band" in base or "itband" in base:
        keywords.extend(["it-band", "itband", "iliotibial", "knie lateral"])
    return list(set(keywords))


# ── Check 5: Strava-Schuhe vs. equipment.md ──────────────────────────


def check_strava_shoes(strava_shoes: list[dict] | None) -> list[dict]:
    if strava_shoes is None:
        return []

    try:
        from app.graphs.shoe_advisor import load_shoe_profiles
    except Exception as e:
        return [_finding(
            MEDIUM, "shoe_profile_load_error", "config/equipment.md",
            evidence=str(e),
            description="Schuhprofile konnten nicht geladen werden — Schuh-Empfehlung defekt",
        )]

    profiles = load_shoe_profiles()
    profiled_ids = {p["strava_id"] for p in profiles}
    active = [s for s in strava_shoes if not s.get("retired")]
    findings: list[dict] = []

    # Aktive Schuhe ohne Profil
    for s in active:
        if s["strava_id"] not in profiled_ids:
            findings.append(_finding(
                MEDIUM,
                "shoe_unprofiled",
                "config/equipment.md",
                evidence=f"strava_id={s['strava_id']} | {s.get('name')} | {s.get('distance_km'):.0f}km",
                canonical_source="Strava (list_shoes)",
                suggested_action="add_profile",
                fix_hint=f"Add profile for strava_id={s['strava_id']} in equipment.md",
                description=f"Active Strava shoe '{s.get('name')}' missing from equipment.md — shoe advisor cannot recommend it",
            ))

    # Profiles that no longer exist in Strava
    strava_ids = {s["strava_id"] for s in strava_shoes}
    for p in profiles:
        if p["strava_id"] not in strava_ids:
            findings.append(_finding(
                LOW,
                "shoe_profile_orphan",
                "config/equipment.md",
                evidence=f"strava_id={p['strava_id']} | {p.get('name')}",
                canonical_source="Strava (list_shoes)",
                suggested_action="remove_profile",
                fix_hint=f"Remove profile for strava_id={p['strava_id']} from equipment.md — shoe no longer in Strava",
                description=f"Profile '{p.get('name')}' in equipment.md has no Strava match",
            ))

    # Shoes near threshold
    for s in active:
        prof = next((p for p in profiles if p["strava_id"] == s["strava_id"]), None)
        if not prof:
            continue
        threshold = prof.get("threshold_km", 800)
        km = s.get("distance_km", 0)
        if km >= threshold * 0.95:
            findings.append(_finding(
                MEDIUM,
                "shoe_threshold_reached",
                "config/equipment.md",
                evidence=f"{s.get('name')}: {km:.0f}/{threshold}km ({km/threshold*100:.0f}%)",
                canonical_source="Strava (list_shoes)",
                suggested_action="rotate_or_retire",
                fix_hint=f"Shoe '{s.get('name')}' near threshold — check rotation or retire",
                description=f"Shoe '{s.get('name')}' at ≥95% of threshold ({km:.0f}/{threshold}km)",
            ))
    return findings


# ── Check 6: Hardcoded Restrictions ──────────────────────────────────


def check_hardcoded_restrictions() -> list[dict]:
    """Findet hartkodierte Restriction-Strings in Agenten/Prompts/Equipment.

    Severity initial MEDIUM — der Auditor-Agent hebt bei stale-Status auf HIGH.
    """
    findings: list[dict] = []
    # TODO(public-split): when framework/ becomes a submodule, framework globs
    # (.claude/agents/, prompts/) must scan FRAMEWORK_ROOT and athlete globs
    # (config/) must scan COACH_HOME. For now FRAMEWORK_ROOT == COACH_HOME.
    for glob in HARDCODE_SCAN_GLOBS:
        scan_root = COACH_HOME if glob.startswith("config/") else FRAMEWORK_ROOT
        for path in sorted(scan_root.glob(glob)):
            rel = str(path.relative_to(scan_root))
            if rel in HARDCODE_SCAN_EXCLUDE:
                continue
            text = _read(path)
            for cat, patterns in RESTRICTION_PATTERNS.items():
                for pattern in patterns:
                    for m in re.finditer(pattern, text, re.IGNORECASE):
                        line = text[: m.start()].count("\n") + 1
                        line_text = text.splitlines()[line - 1] if line - 1 < len(text.splitlines()) else ""
                        findings.append(_finding(
                            MEDIUM,
                            "hardcoded_restriction",
                            rel,
                            source_line=line,
                            evidence=f"[{cat}] {line_text.strip()[:160]}",
                            canonical_source="config/athlete_static.md (risk zones + breakdown)",
                            suggested_action="verify_against_athlete_static",
                            fix_hint=(
                                "Auditor agent: compare restriction string against current status "
                                f"in athlete_static.md. If status 'aktiv' → OK. If resolved → "
                                "remove the reference or replace with a pointer to athlete_static."
                            ),
                            description=f"Hardcoded {cat} restriction in {rel}:{line}",
                        ))
    return findings


# ── Check 7: Erholungswoche-Konsistenz ────────────────────────────────


def check_log_vs_history(activities: list[dict] | None) -> list[dict]:
    """Drift zwischen exercise_log.md / exercise_progressions.md und Type-History.

    Hintergrund: Specs lasen frueher Sets/Reps aus exercise_log.md/exercise_progressions.md
    (Snapshots vom Videoanalyse-Moment) statt aus der Type-History (per-Session
    geschrieben). Das fuehrte in realer Anwendung zu Volumen-Regressionen
    bei mehreren Core-/Stabilisations-Uebungen.

    Heuristik: Wenn ein Eintrag in exercise_progressions.md / exercise_log.md
    eine Datums-Markierung enthaelt (`(YYYY-MM-DD)` oder `**Letztes Video:** YYYY-MM-DD`),
    UND die Activities zeigen mind. eine spaetere Session in der die Uebung
    gemacht wurde → MEDIUM-Finding (Doku potenziell veraltet).
    """
    if not activities:
        return []

    findings: list[dict] = []
    progressions_text = _read(resolve_config("exercise_progressions.md"))
    log_text = _read(resolve_config("exercise_log.md"))

    # Sammle alle (uebung_name, doc_date, source_file, source_line, evidence)
    # aus exercise_progressions.md
    entries: list[dict] = []

    # Format in exercise_progressions.md: "### Uebungsname" gefolgt von
    # "**Aktueller Stand:** ... (YYYY-MM-DD)". Auch #### Sub-Sections (z.B.
    # Maximalkraft-Varianten unter einem Block-Header) zaehlen, sonst landet
    # der innere Aktueller-Stand-Eintrag faelschlich beim Eltern-Header,
    # dessen Name ein Schedule-Label ist (z.B. "Pull/Grip-Block (1x/Woche)").
    section_re = re.compile(
        r"^####?\s+(.+?)\s*\n(.*?)(?=^####?\s|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    # Allow trailing metadata inside the parenthesis, e.g.
    # "(DD.MM.YYYY, iNNNNNN, Athlet-Edit)" as left behind by
    # sync_description_drift.py's _stamp_date. The optional group MUST start
    # with `,` or whitespace (not `)`) so we don't greedily span from one
    # bracket to a later closing one — which would skip the inner `(date)`
    # and pick up text between the two date stamps.
    iso_date_re = re.compile(r"\((\d{4}-\d{2}-\d{2})(?:[,\s][^)]*)?\)")
    de_date_re = re.compile(r"\((\d{2})\.(\d{2})\.(\d{4})(?:[,\s][^)]*)?\)")

    def _parse_doc_date(s: str):
        """Erkennt sowohl ISO (YYYY-MM-DD) als auch DE-Format (DD.MM.YYYY).

        Gibt die **spaeteste** Datums-Markierung der Zeile zurueck. Hintergrund:
        sync_description_drift.py haengt einen neuen `(DD.MM.YYYY, iNNN, Athlet-Edit)`-
        Stamp ans Zeilenende an, ohne den urspruenglichen Datums-Marker in der
        Stand-Beschreibung zu entfernen. Wenn wir nur die erste Datums-Klammer
        lesen, sieht der Audit das Update nicht und meldet faelschlich weiter
        Drift. Spaetestes Datum gewinnt.
        """
        from datetime import date as _date
        candidates: list[_date] = []
        for m in iso_date_re.finditer(s):
            try:
                candidates.append(_date.fromisoformat(m.group(1)))
            except ValueError:
                pass
        for m in de_date_re.finditer(s):
            try:
                candidates.append(_date(int(m.group(3)), int(m.group(2)), int(m.group(1))))
            except ValueError:
                pass
        return max(candidates) if candidates else None

    for sec in section_re.finditer(progressions_text):
        name = sec.group(1).strip()
        body = sec.group(2)
        # Nur Eintraege mit datiertem "Aktueller Stand"
        m_state = re.search(r"\*\*Aktueller Stand:\*\*[^\n]*", body)
        if not m_state:
            continue
        doc_date = _parse_doc_date(m_state.group(0))
        if doc_date is None:
            continue
        # Zeile im File ermitteln
        line_no = progressions_text[: sec.start()].count("\n") + 1
        entries.append({
            "name": name,
            "doc_date": doc_date,
            "source_file": "config/exercise_progressions.md",
            "source_line": line_no,
            "evidence": m_state.group(0).strip(),
        })

    # exercise_log.md: "## Uebungsname" + "**Letztes Video:** YYYY-MM-DD"
    log_section_re = re.compile(
        r"^##\s+(.+?)\s*\n(.*?)(?=^##\s|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    log_date_re = re.compile(r"\*\*Letztes Video:\*\*\s*(\d{4}-\d{2}-\d{2})")
    for sec in log_section_re.finditer(log_text):
        name = sec.group(1).strip()
        body = sec.group(2)
        m_date = log_date_re.search(body)
        if not m_date:
            continue
        try:
            from datetime import date as _date
            doc_date = _date.fromisoformat(m_date.group(1))
        except ValueError:
            continue
        line_no = log_text[: sec.start()].count("\n") + 1
        # Nur Eintraege bei denen explizit Sets/Reps in der Drill/Progression-Zeile stehen
        # (sonst ist es ein reiner Form-Eintrag und nicht progressions-relevant)
        m_progression = re.search(r"\*\*Progression\*\*[^:]*:\s*([^\n]+)", body)
        if not m_progression:
            continue
        prog_text = m_progression.group(1)
        if not re.search(r"\d+x\d+|\d+\s*x\s*\d+|\d+\s*Reps?|\d+\s*Wdh", prog_text, re.IGNORECASE):
            continue  # keine konkrete Sets/Reps-Aussage
        entries.append({
            "name": name,
            "doc_date": doc_date,
            "source_file": "config/exercise_log.md",
            "source_line": line_no,
            "evidence": f"Letztes Video: {m_date.group(1)} | Progression-Zeile: {prog_text.strip()}",
        })

    # Activities scannen: hat der Athlet die Uebung NACH doc_date gemacht?
    # Activity-Description nach Uebungs-Aliasen durchsuchen
    def _normalize(s: str) -> str:
        s = s.lower()
        # Klammer-Zusaetze entfernen
        s = re.sub(r"\(.+?\)", "", s)
        s = re.sub(r"[^a-z0-9 ]", " ", s)
        return re.sub(r"\s+", " ", s).strip()

    # Generic words that match too many descriptions — exclude from token
    # matching to reduce false positives (e.g. "balance" matches every
    # Balance-Board-Workout name).
    _GENERIC_TOKENS = {
        "balance", "reach", "hold", "press", "row", "core", "block",
        "hand", "grip", "curl", "lift", "squat", "stand", "step",
        "side", "front", "back", "rear",
    }

    for entry in entries:
        norm_name = _normalize(entry["name"])
        # Tokens > 4 chars, minus generic stop words. If nothing remains
        # after filtering → fall back to all >3-char tokens.
        specific_tokens = [t for t in norm_name.split() if len(t) > 4 and t not in _GENERIC_TOKENS]
        fallback_tokens = [t for t in norm_name.split() if len(t) > 3]
        key_tokens = specific_tokens or fallback_tokens
        if not key_tokens:
            key_tokens = [norm_name]

        last_seen: "datetime.date | None" = None
        for act in activities:
            desc = (act.get("description") or "")
            if not desc:
                continue
            norm_desc = _normalize(desc)
            # ALL specific tokens must be present — avoids false
            # positives where only a single generic word matches
            # ("balance" in a balance-board workout name).
            if not all(t in norm_desc for t in key_tokens):
                continue
            # Datum extrahieren
            start = act.get("start_date_local") or act.get("start_date") or ""
            try:
                from datetime import date as _date
                act_date = _date.fromisoformat(start[:10])
            except (ValueError, TypeError):
                continue
            if last_seen is None or act_date > last_seen:
                last_seen = act_date

        if last_seen is None or last_seen <= entry["doc_date"]:
            continue  # Doku ist aktuell oder Uebung wurde nicht gemacht

        days_diff = (last_seen - entry["doc_date"]).days
        # Nur bei deutlichem Drift melden (>= 5 Tage)
        if days_diff < 5:
            continue

        findings.append(_finding(
            MEDIUM,
            "exercise_log_drift",
            entry["source_file"],
            source_line=entry["source_line"],
            evidence=(
                f"Eintrag fuer „{entry['name']}“\n"
                f"  Doku-Stand: {entry['doc_date'].isoformat()}\n"
                f"  Letzte Activity mit Uebung: {last_seen.isoformat()} (+{days_diff} Tage)\n"
                f"  {entry['evidence']}"
            ),
            canonical_source="Type-History (Activity-Descriptions)",
            suggested_action="update_doc_from_history",
            fix_hint=(
                f"Uebung „{entry['name']}“ wurde nach dem dokumentierten "
                f"Stand ({entry['doc_date']}) noch {days_diff} Tage spaeter trainiert "
                f"({last_seen}). `{entry['source_file']}:{entry['source_line']}` "
                f"auf den Stand der letzten Activity-Description angleichen — Sets/Reps/RPE/Hold "
                f"aus der Activity uebernehmen. Empfohlen: `python3 scripts/sync_description_drift.py "
                f"--activity-id <ID der spaetesten Session>` — der Parser liftet auch "
                f"Hold-Time-Progressions (TUT-Vektor)."
            ),
            description=(
                f"Doku-Eintrag „{entry['name']}“ in `{entry['source_file']}` "
                f"ist potenziell veraltet — Athlet hat die Uebung seit dem dokumentierten "
                f"Stand mehrfach trainiert."
            ),
        ))

    return findings


def check_config_drift() -> list[dict]:
    """Cross-source drift between athlete_static.md, CLAUDE.md and code constants.

    Compares the same numerical/factual value across multiple sources and
    reports any deviation as a finding. Define new facts below in
    `config_facts` — generic, no code change needed for the check itself.
    """
    static_text = _read(resolve_config("athlete_static.md"))
    # CLAUDE.md lives in COACH_HOME (athlete wrapper). If absent, fall back to
    # framework default (e.g. when running against config.example/ only).
    claude_md_path = COACH_HOME / "CLAUDE.md"
    if not claude_md_path.exists():
        claude_md_path = FRAMEWORK_ROOT / "CLAUDE.md"
    claude_text = _read(claude_md_path)

    sources_text = {
        "config/athlete_static.md": static_text,
        "CLAUDE.md": claude_text,
    }

    # Fact definition: one fact, N sources each with a regex.
    # Severity applies to the whole fact, not per source.
    config_facts = [
        {
            "name": "athlete_weight_kg",
            "label": "Body weight (kg)",
            "severity": LOW,
            "extractors": [
                ("config/athlete_static.md", r"(?:Körpergewicht|Body\s*weight):\s*(\d{2,3})\s*kg"),
                # In comments: "× 75 kg"
                ("CLAUDE.md", r"×\s*(\d{2,3})\s*kg"),
            ],
        },
    ]

    # Value normalisation: convert the same quantity to a common unit
    def _normalize(name: str, source: str, raw: str) -> float | None:
        try:
            val = float(raw.replace(",", "."))
        except ValueError:
            return None
        return val

    findings: list[dict] = []

    for fact in config_facts:
        extracted: dict[str, tuple[str, float]] = {}  # source -> (raw_match, normalized_value)
        for source_path, pattern in fact["extractors"]:
            text = sources_text.get(source_path, "")
            if not text:
                continue
            m = re.search(pattern, text, re.IGNORECASE)
            if not m:
                continue
            raw = m.group(1)
            normalized = _normalize(fact["name"], source_path, raw)
            if normalized is None:
                continue
            extracted[source_path] = (raw, normalized)

        if len(extracted) < 2:
            # only 1 source found — no drift possible, but fact may be incomplete
            continue

        unique_values = {v[1] for v in extracted.values()}
        if len(unique_values) <= 1:
            # all sources agree — no drift
            continue

        # Drift: at least two sources disagree
        # Majority value as likely truth, deviating sources as drift
        from collections import Counter
        cnt = Counter(v[1] for v in extracted.values())
        likely_canon, _ = cnt.most_common(1)[0]
        canon_sources = [s for s, (_, v) in extracted.items() if v == likely_canon]
        drift_sources = [(s, raw) for s, (raw, v) in extracted.items() if v != likely_canon]

        for drift_source, drift_raw in drift_sources:
            evidence_lines = [
                f"{drift_source}: {drift_raw}",
                f"other sources: " + " / ".join(
                    f"{s}={extracted[s][0]}" for s in canon_sources
                ),
            ]
            findings.append(_finding(
                fact["severity"],
                "config_drift",
                drift_source,
                evidence="\n".join(evidence_lines),
                canonical_source=" / ".join(canon_sources),
                suggested_action="align_values",
                fix_hint=(
                    f"{fact['label']}: `{drift_source}` has `{drift_raw}`, "
                    f"other sources say `{extracted[canon_sources[0]][0]}` "
                    f"({len(canon_sources)} source(s)). Align value in `{drift_source}` "
                    f"OR deliberately update all other sources."
                ),
                description=(
                    f"Drift in fact `{fact['name']}` ({fact['label']}). "
                    f"At least two sources have different values — "
                    f"leads to inconsistency between docs and code behaviour."
                ),
            ))

    return findings


def check_deload_consistency() -> list[dict]:
    """Checks whether recovery-week status is consistent (date vs. active flag)."""
    text = _read(resolve_config("athlete_status.md"))
    m = re.search(r"## Erholungswoche-Status\n(.*?)(?=\n##|\Z)", text, re.DOTALL)
    if not m:
        return []
    section = m.group(1)
    aktiv = re.search(r"\*\*aktiv:\*\*\s*(\S+)", section)
    ende = re.search(r"\*\*ende_geplant:\*\*\s*(\S+)", section)
    if not aktiv or not ende:
        return []
    aktiv_val = aktiv.group(1).strip().lower()
    ende_val = ende.group(1).strip()
    findings: list[dict] = []
    if aktiv_val == "ja" and re.match(r"\d{4}-\d{2}-\d{2}", ende_val):
        from datetime import date as _date
        try:
            ende_date = _date.fromisoformat(ende_val)
            if ende_date < _date.today():
                findings.append(_finding(
                    MEDIUM,
                    "deload_expired",
                    "config/athlete_status.md",
                    evidence=f"aktiv: ja, ende_geplant: {ende_val} (past)",
                    canonical_source="Today",
                    suggested_action="reset_deload",
                    fix_hint="Reset recovery-week status to aktiv: nein",
                    description="Recovery-week flag is 'aktiv: ja' but ende_geplant is in the past",
                ))
        except ValueError:
            pass
    return findings


# ── Check: Blocked exercises in active pools ─────────────────────────


def _parse_progression_exercises_from_log() -> list[dict]:
    """Parses exercise_log.md for entries with Status: progression.

    Returns: [{
      'name': str,
      'reason': str,
      'current_level': int,
      'stages': [{'level': int, 'text': str}, ...],
    }, ...]
    """
    text = _read(resolve_config("exercise_log.md"))
    entries: list[dict] = []
    sections = re.split(r"\n(?=## )", text)
    for section in sections:
        if not section.startswith("## "):
            continue
        if not re.search(r"\*\*Status:\*\*\s*progression", section, re.IGNORECASE):
            continue
        header = section.splitlines()[0].lstrip("# ").strip()
        if not header or header == "{Übung}" or header == "{Exercise}":
            continue
        reason_m = re.search(r"\*\*Befund:\*\*\s*(.+?)(?:\n\*\*|\Z)", section, re.DOTALL)
        reason = (reason_m.group(1).strip()[:200] if reason_m else "")
        level_m = re.search(r"\*\*Aktuelles Level:\*\*\s*Stufe\s*(\d+)", section, re.IGNORECASE)
        current_level = int(level_m.group(1)) if level_m else 1
        # Stages aus '- **Stufe N**: text [match: phrase1, phrase2]' Bullet-Liste
        stages: list[dict] = []
        for m in re.finditer(r"-\s+\*\*Stufe\s*(\d+)[^:*]*\*\*:\s*(.+)", section):
            text = m.group(2).strip()
            # Extract [match: phrase1, phrase2] hints
            match_m = re.search(r"\[match:\s*([^\]]+)\]", text)
            phrases: list[str] = []
            if match_m:
                phrases = [p.strip().lower() for p in match_m.group(1).split(",") if p.strip()]
            stages.append({"level": int(m.group(1)), "text": text, "match_phrases": phrases})
        entries.append({
            "name": header,
            "reason": reason,
            "current_level": current_level,
            "stages": stages,
        })
    return entries


def _name_tokens(name: str) -> set[str]:
    """Tokenize an exercise name to lower-case alphanumeric tokens (≥3 chars)."""
    tokens = re.findall(r"[a-zA-ZäöüÄÖÜß0-9]+", name.lower())
    # Filter stop words and short tokens
    stop = {"und", "oder", "auf", "mit", "der", "die", "das", "ein", "eine", "im", "vor", "nach"}
    return {t for t in tokens if len(t) >= 3 and t not in stop}


def _scannable_lines_from_pool(path: Path) -> list[tuple[int, str]]:
    """Extracts exercise lines from a pool file (one exercise per line).

    JSON files: reads description strings, splits on real newlines + | separators.
    Markdown files: reads every line.
    Returns: [(approx_line_num, scan_line), ...]
    """
    # Use path.suffix directly — resolve_config() can return a path outside
    # ROOT (Wrapper-CONFIG_DIR is a sibling of framework/), which makes
    # `path.relative_to(ROOT)` raise ValueError and previously crashed the
    # PROGRESSION_OVERSHOOT check whenever a progression entry triggered it.
    if path.suffix == ".json":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []
        out: list[tuple[int, str]] = []
        # Walk all string values, looking for "description"-typed contents
        def _walk(obj: Any, line_hint: int = 1) -> None:
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if isinstance(v, str) and len(v) > 30:
                        for sub in re.split(r"\n|(?<!\d)\|", v):
                            sub = sub.strip()
                            if sub:
                                out.append((line_hint, sub))
                    else:
                        _walk(v, line_hint)
            elif isinstance(obj, list):
                for v in obj:
                    _walk(v, line_hint)
        _walk(data)
        return out
    # Markdown-Fallback: per Zeile
    text = path.read_text(encoding="utf-8")
    return [(i, line) for i, line in enumerate(text.splitlines(), start=1) if line.strip()]


def _is_block_annotation(line: str) -> bool:
    """True if the line is a block/lock annotation rather than an active exercise."""
    lower = line.lower()
    # Direct block keywords
    if any(s in lower for s in ("gesperrt", "verboten", "blockiert", "siehe _constraints")):
        return True
    # Parenthesised annotations with block hint
    paren_text = " ".join(re.findall(r"\(([^)]*)\)", lower))
    if paren_text and any(s in paren_text for s in ("gesperrt", "verboten", "blockiert")):
        return True
    return False


# ── Check: Override-Drift zwischen Framework-Defaults und Wrapper ──────────

OVERRIDE_FILES = ["training_paradigms.md", "exercise_progressions.md"]

# Patterns that should NOT appear in framework defaults (athlete-specific)
_FRAMEWORK_LEAK_PATTERNS = [
    (re.compile(r"\b\d{2,3}\s*[-–]\s*\d{2,3}\s*bpm\b", re.I), "raw HR range"),
    (re.compile(r"≥\s*\d{3}\s*bpm\b", re.I), "raw HR threshold"),
    (re.compile(r"\b\d{2}\.\d{2}\.20\d{2}\b"), "specific date"),
    (re.compile(r"\bKW\s*\d{1,2}\b"), "calendar week reference"),
    (re.compile(r"^- \*\*Aktueller Stand:\*\*", re.M), "Aktueller-Stand tracking"),
]


def _normalize_heading(h: str) -> str:
    """Normalize a heading by stripping athlete-specific tokens.

    Used for fuzzy matching between framework (generic) and wrapper (often
    dated) heading variants. Example:
        "Strength-Block (1×/Woche, ab KW42 = 14.10.2025)"
            → "Strength-Block (1×/Woche)"
        "Cadence (Stand 01.03.2025 — KEINE Vorgabe mehr in Workouts):"
            → "Cadence (KEINE Vorgabe mehr in Workouts)"
    """
    # KW + optional " = DD.MM.YYYY" suffix, including a preceding ", ab "
    h = re.sub(r",?\s*ab\s+KW\s*\d{1,2}\s*(?:=\s*\d{2}\.\d{2}\.\d{4})?", "", h)
    h = re.sub(r"\bKW\s*\d{1,2}\b", "", h)
    # "(Stand|Update|Korrektur) DD.MM.YYYY" with optional trailing " — "
    h = re.sub(r"\b(?:Stand|Update|Korrektur)\s+\d{2}\.\d{2}\.\d{4}\s*(?:[—-]\s*)?", "", h)
    # "ab DD.MM.YYYY," (e.g., "(ab 25.04.2026, permanent)")
    h = re.sub(r"\bab\s+\d{2}\.\d{2}\.\d{4}\s*,?\s*", "", h)
    # Standalone DD.MM.YYYY
    h = re.sub(r"\b\d{2}\.\d{2}\.\d{4}\b", "", h)
    # Cleanup: collapse spaces, fix empty parens, leading/trailing junk
    h = re.sub(r"[ \t]{2,}", " ", h)
    h = re.sub(r"\(\s+", "(", h)
    h = re.sub(r"\s+\)", ")", h)
    h = re.sub(r"\(\s*\)", "", h)
    h = re.sub(r",\s*\)", ")", h)
    return h.strip().rstrip(":,— ")


def _extract_headings(text: str) -> set[str]:
    """Return set of normalized H2 + H3 heading text.

    Headings are normalized via _normalize_heading so that wrapper variants
    with athlete-specific date/KW context match the framework's generic form.
    """
    return {
        _normalize_heading(m.group(1))
        for m in re.finditer(r"^#{2,3}\s+(.+?)\s*$", text, re.M)
    }


def check_override_drift() -> list[dict]:
    """Drift between framework defaults and wrapper overrides.

    Four drift classes:
      - framework_leak: athlete content in framework version
      - pointless_override: wrapper copy byte-identical to framework
      - wrapper_missing_section: wrapper lags behind framework
      - missing_tracking: exercise_progressions without current-state entries
    """
    findings: list[dict] = []
    for filename in OVERRIDE_FILES:
        fw_path = CONFIG_FALLBACK / filename
        wrap_path = CONFIG_DIR / filename

        if not fw_path.exists():
            continue
        fw_text = fw_path.read_text(encoding="utf-8")

        # Check 1: framework_leak — athlete markers in framework
        for pattern, label in _FRAMEWORK_LEAK_PATTERNS:
            for m in pattern.finditer(fw_text):
                # Skip if context contains a legitimate reference
                ctx = fw_text[max(0, m.start() - 100):m.end() + 50]
                if "athlete_static.md" in ctx or "athlete_overrides" in ctx:
                    continue
                line = fw_text.count("\n", 0, m.start()) + 1
                findings.append(_finding(
                    MEDIUM,
                    "framework_leak",
                    f"framework/config.example/{filename}",
                    source_line=line,
                    evidence=f"{label}: {m.group(0)!r}",
                    canonical_source=f"config/{filename} or config/athlete_static.md",
                    suggested_action="genericize",
                    fix_hint=(
                        f"Remove athlete-specific {label} from framework version; "
                        "move to wrapper override or athlete_static.md if needed."
                    ),
                    description=f"Framework default contains {label} — belongs in wrapper override.",
                ))

        if not wrap_path.exists():
            continue
        wrap_text = wrap_path.read_text(encoding="utf-8")

        # Check 2: pointless_override — wrapper copy identical to framework
        if fw_text == wrap_text:
            findings.append(_finding(
                LOW,
                "pointless_override",
                f"config/{filename}",
                evidence="byte-identical to framework default",
                canonical_source=f"framework/config.example/{filename}",
                suggested_action="delete_wrapper_copy",
                fix_hint="Delete wrapper copy — loader fallback delivers identical file from framework.",
                description="Wrapper override with no added value: only creates future drift risk.",
            ))
            continue

        # Check 3: wrapper_missing_section — missing headings in wrapper.
        # Override mechanism: wrapper can declare deliberate override
        # decisions (translation, exercise-replaced, not-relevant for this
        # athlete) via HTML comment block. Format:
        #
        #     <!-- audit-skip-missing:
        #       - Latzug (Physio-Protokoll)   # replaced by Scapular Pullups
        #       - HR zones                    # translated as "HR-Zonen"
        #     -->
        #
        # Headings listed therein are removed from the missing list
        # BEFORE the finding is generated.
        fw_headings = _extract_headings(fw_text)
        wrap_headings = _extract_headings(wrap_text)
        skip_block_re = re.compile(
            r"<!--\s*audit-skip-missing:\s*(.+?)\s*-->",
            re.DOTALL | re.IGNORECASE,
        )
        skip_list: set[str] = set()
        for m in skip_block_re.finditer(wrap_text):
            for raw in m.group(1).splitlines():
                line = raw.strip()
                # Strip leading "- " / "* " bullet markers and trailing
                # comments after "#".
                line = re.sub(r"^[\-\*]\s*", "", line)
                line = re.sub(r"\s+#.*$", "", line)
                if line:
                    skip_list.add(line)
        missing = sorted(fw_headings - wrap_headings - skip_list)
        if missing:
            preview = ", ".join(repr(h) for h in missing[:3])
            if len(missing) > 3:
                preview += f", … (+{len(missing) - 3})"
            findings.append(_finding(
                MEDIUM,
                "wrapper_missing_section",
                f"config/{filename}",
                evidence=f"{len(missing)} section(s) missing: {preview}",
                canonical_source=f"framework/config.example/{filename}",
                suggested_action="sync_wrapper",
                fix_hint=(
                    "Add missing sections from framework to wrapper override OR "
                    "mark as deliberately overridden via "
                    "`<!-- audit-skip-missing: \\n - <heading>\\n -->` block in the wrapper file."
                ),
                description=(
                    "Framework was extended with sections missing from wrapper override "
                    "— athlete does not see the new rules."
                ),
            ))

        # Check 4 (file-specific): exercise_progressions.md without tracking
        if filename == "exercise_progressions.md":
            wrap_tracking = len(re.findall(r"^- \*\*Aktueller Stand:\*\*", wrap_text, re.M))
            if wrap_tracking == 0:
                findings.append(_finding(
                    LOW,
                    "missing_tracking",
                    f"config/{filename}",
                    evidence="0 current-state entries in wrapper override",
                    canonical_source="(wrapper is the tracking location)",
                    suggested_action="add_tracking_or_delete",
                    fix_hint=(
                        "Add current-state entries per exercise OR delete wrapper override "
                        "(tracking then only via type history)."
                    ),
                    description=(
                        "Wrapper override for exercise_progressions without tracking — "
                        "the key added value of the override is missing."
                    ),
                ))

    return findings


def check_progression_overshoot() -> list[dict]:
    """Finds pool entries containing stages above `current_level + 1` of a
    progression-marked exercise.

    Detection: For each exercise with Status: progression in exercise_log.md,
    all stage texts from the stage plan are extracted. Pool files (balance_pool.json,
    exercise_progressions.md) are scanned line by line; if the tokens of a stage
    match and its level > current_level + 1 → HIGH finding.

    Why +1: The pool may contain the next stage as a test stimulus, but no
    stages further out (those would be too large a jump).
    """
    entries = _parse_progression_exercises_from_log()
    if not entries:
        return []

    pool_files = ["balance_pool.json", "exercise_progressions.md"]
    findings: list[dict] = []
    for entry in entries:
        max_allowed = entry["current_level"] + 1
        for stage in entry["stages"]:
            if stage["level"] <= max_allowed:
                continue
            phrases = stage.get("match_phrases") or []
            if not phrases:
                # Without explicit [match: ...] hints no check (false-positive
                # risk too high with token heuristics). Coach maintains
                # match hints in exercise_log.md.
                continue
            for rel in pool_files:
                try:
                    path = resolve_config(rel)
                except FileNotFoundError:
                    continue
                if not path.exists():
                    continue
                for line_num, line in _scannable_lines_from_pool(path):
                    if _is_block_annotation(line):
                        continue
                    line_lower = line.lower()
                    if all(p in line_lower for p in phrases):
                        findings.append(_finding(
                            HIGH,
                            "progression_overshoot",
                            rel,
                            source_line=line_num,
                            evidence=f"[{entry['name']} Stufe {stage['level']}] {line.strip()[:160]}",
                            canonical_source="config/exercise_log.md (Status: progression)",
                            suggested_action="reduce_to_current_level",
                            fix_hint=(
                                f"Exercise '{entry['name']}' is at stage {entry['current_level']} "
                                f"(max allowed: stage {max_allowed}). Pool entry contains "
                                f"stage {stage['level']} ({stage['text'][:80]}…) — jump too large. "
                                "Adjust pool to current level or trigger re-evaluation."
                            ),
                            description=(
                                f"Progression overshoot: exercise '{entry['name']}' in {rel}:{line_num} "
                                f"at stage {stage['level']}, current level is only {entry['current_level']}"
                            ),
                        ))
                        break
    return findings


# Backward-compat alias (CHECK_MAP uses the old name)
check_blocked_exercises = check_progression_overshoot


# ── Prompt-Drift: HR-Zone-Briefing & andere kanonische Phrasen ────────

# Canonical phrases that MUST appear identically wherever they appear.
# Drift happens when one specialist's prompt slowly diverges from the
# canonical wording — semantically still close but no longer copy-paste
# equivalent. The drift-linter does not enforce that *every* prompt
# carries the phrase, only that wherever the phrase *appears*, it
# matches the canonical form byte-for-byte.
#
# To add a new canonical phrase: pick a short, unambiguous trigger
# substring (`trigger`) that uniquely identifies the section, then
# the canonical full sentence (`canonical`). The linter scans every
# `prompts/*.yaml` and `agents/*.md` file, picks lines containing the
# trigger, and flags any line that doesn't match the canonical form.
_CANONICAL_PHRASES: list[dict[str, str]] = [
    {
        "label": "hr_zone_briefing",
        "trigger": "HR zones from `context.hrZones`",
        "canonical": (
            "Pass HR zones from `context.hrZones` verbatim — never reconstruct "
            "from memory, never compute LTHR or zone bounds from recall."
        ),
    },
    {
        "label": "warmup_drill_dedup",
        "trigger": "drill belongs in the warmup",
        "canonical": (
            "Running drills (A-skips, leg swings, hip flexor) belong in exactly "
            "one warmup per day — the workout with the highest matching stimulus."
        ),
    },
]


def check_prompt_drift() -> list[dict]:
    """Drift scanner for canonical phrases across prompts and agents.

    Searches all `framework/prompts/*.yaml` and `framework/agents/*.md`
    for trigger substrings; every matching line must be byte-identical to
    the `canonical` form. Mismatches are flagged as MEDIUM findings.

    No automatic fix — the fixer does not derive the canonical form from
    code but from this module. When triaging, manually update to the
    `canonical` line.
    """
    findings: list[dict] = []

    scan_dirs = [
        FRAMEWORK_ROOT / "prompts",
        FRAMEWORK_ROOT / "agents",
    ]
    files: list[Path] = []
    for d in scan_dirs:
        if not d.exists():
            continue
        files.extend(sorted(d.glob("*.yaml")))
        files.extend(sorted(d.glob("*.md")))

    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue

        for phrase in _CANONICAL_PHRASES:
            trigger = phrase["trigger"]
            canonical = phrase["canonical"]
            label = phrase["label"]
            if trigger not in text:
                continue

            # Compare on a line basis. We allow the canonical wording to span
            # multiple consecutive lines in the source file (markdown wraps).
            for line_num, line in enumerate(text.splitlines(), 1):
                if trigger not in line:
                    continue
                stripped = line.strip()
                # The line must either *be* the canonical form, OR start with
                # it (allowing trailing commentary in YAML literal-blocks).
                if stripped != canonical.strip() and not stripped.startswith(canonical.strip()):
                    rel = path.relative_to(FRAMEWORK_ROOT).as_posix()
                    findings.append(_finding(
                        MEDIUM,
                        "prompt_drift",
                        f"framework/{rel}",
                        source_line=line_num,
                        evidence=f"[{label}] {stripped[:160]}",
                        canonical_source=f"_CANONICAL_PHRASES[{label}]",
                        suggested_action="replace_with_canonical",
                        fix_hint=(
                            f"Replace the line with the canonical wording for "
                            f"'{label}': {canonical}"
                        ),
                        description=(
                            f"Prompt-Drift: Treffer auf '{trigger}', aber Zeile "
                            f"weicht von kanonischer Form ab."
                        ),
                    ))
    return findings


# ── Online: intervals.icu + Strava fetchen ───────────────────────────


async def _fetch_online() -> dict[str, Any]:
    from app.api.intervals_cache import CachedIntervalsClient
    from app.api.strava_client import StravaClient
    from app.config import settings

    athlete_id = settings.intervals_icu_athlete_id
    icu = CachedIntervalsClient(athlete_id)

    from datetime import date, timedelta
    today = date.today()
    oldest = (today - timedelta(weeks=4)).isoformat()
    newest = today.isoformat()

    async def _shoes() -> list[dict]:
        if not settings.strava_client_id or not settings.strava_refresh_token:
            return []
        try:
            return await StravaClient().list_shoes()
        except Exception as e:
            logger.warning("strava fetch failed: %s", e)
            return []

    try:
        notes, athlete_settings, shoes, activities = await asyncio.gather(
            icu.get_notes(oldest, newest),
            icu.get_athlete_settings(),
            _shoes(),
            icu.get_activities(oldest, newest),
        )
    except Exception as e:
        logger.warning("online fetch failed: %s", e)
        return {"notes": None, "athlete_settings": None, "shoes": None, "activities": None, "error": str(e)}

    return {"notes": notes, "athlete_settings": athlete_settings, "shoes": shoes, "activities": activities}


# ── Orchestrierung ───────────────────────────────────────────────────


# ---------------------------------------------------------------------------
# POLICY_COVERAGE — verhindert Drift zwischen CLAUDE.md (Policy) und
# Code/Commands (Enforcement). Jede `(mandatory)`-Section im CLAUDE.md muss
# entweder Code-anchored sein (Funktion/Script genannt) ODER von einem
# `commands/*.md`-Workflow referenziert werden ODER explizit als
# "head-coach judgment" markiert. Sektionen ohne Anker sind Drift-Kandidaten.
# ---------------------------------------------------------------------------

_POLICY_HEADING_RE = re.compile(
    r"^(#{2,4})\s+(.+?)\s+\((mandatory|MANDATORY)\)\s*$",
    re.MULTILINE,
)

# Inline bold marker: `**Daily balance rotation (mandatory ...):**` — the
# drift class that caused the balance unit to vanish (no `###` heading,
# therefore easy to overlook).
_POLICY_INLINE_RE = re.compile(
    r"^\*\*(.+?)\s+\((mandatory|MANDATORY)[^)]*\)\s*[:.]?\*\*",
    re.MULTILINE,
)

# Heuristic for code anchors: detects mentions of concrete scripts, modules,
# functions, helpers, tools or typed data sources that serve as enforcement
# paths.
_CODE_ANCHOR_PATTERNS = [
    r"\b[a-z_][a-z0-9_]*\.py\b",                          # script.py
    r"\b(?:app|scripts|framework)/[a-z0-9_/]+\.py\b",     # path/to/module.py
    r"`[A-Za-z_][A-Za-z0-9_]*::[A-Za-z_][A-Za-z0-9_]*`",  # `module::function`
    r"`_[a-z][a-z0-9_]+\(",                               # `_helper_func(`
    r"\bcontext\.[a-zA-Z]+",                              # context.weeklyHardReizeBalance
    r"\bcontext\[['\"]",                                  # context['xxx']
    r"\bconfig/[a-z_]+\.[a-z]+\b",                        # config/foo.md / .json
    r"\bsettings\.[a-z_]+",                               # settings.xxx
    r"\bnotify_[a-z_]+",                                  # alerts
    r"\bescape_for_prompt",                               # sanitize boundary
    r"\bCron(?:Create|Delete|List)\b",                    # tool names
    r"\bpost_message\.py\b",
    r"\bvalidate_plan\.py\b",
    r"\bpush_workouts\.py\b",
    r"\bCode:\s",                                         # Explicit "Code:" tag
    r"\bImplementation:\s",
    r"\bimplemented in\b",
    r"\benforced (?:in|by) code\b",
    r"\benforces (?:this )?in code\b",
]

# Heuristic for policy-only markers — allows explicit opt-out from
# the audit when the coach-judgment character is documented.
_POLICY_ONLY_PATTERNS = [
    r"\bhead[- ]coach judgment\b",
    r"\bcoach judgment\b",
    r"\bjudgment only\b",
    r"\bpolicy only\b",
    r"\bno code possible\b",
    r"\bnot mechan(?:isable|izable)\b",
]


def _extract_mandatory_sections(text: str) -> list[dict[str, Any]]:
    """Return one dict per `(mandatory)` section in CLAUDE.md.

    Includes both `### Title (mandatory)` headings AND inline
    `**Title (mandatory ...):**` bold markers (the latter was the
    Balance-Drift entry point on 2026-05-18).

    Each dict carries: heading, body, line.
    """
    sections: list[dict[str, Any]] = []

    # Heading-level (mandatory)
    matches = list(_POLICY_HEADING_RE.finditer(text))
    for i, m in enumerate(matches):
        level = len(m.group(1))
        title = m.group(2).strip()
        start = m.start()
        line_no = text[:start].count("\n") + 1
        end = len(text)
        for nxt in matches[i + 1:]:
            if len(nxt.group(1)) <= level:
                end = nxt.start()
                break
        body = text[m.end():end]
        next_higher = re.search(rf"^#{{1,{level}}}\s", body, re.MULTILINE)
        if next_higher:
            body = body[: next_higher.start()]
        sections.append({
            "heading": title,
            "body": body,
            "line": line_no,
        })

    # Inline-Bold (mandatory): consume until next blank-block break or next
    # bold-marker / heading. We use a heuristic "until next double newline +
    # one more block" to capture the relevant body.
    for m in _POLICY_INLINE_RE.finditer(text):
        title = m.group(1).strip()
        start = m.start()
        line_no = text[:start].count("\n") + 1
        # Body until next heading (any level), next inline bold marker, or
        # end of file — keep it compact (max ~30 lines).
        tail = text[m.end():]
        # Stop at next heading
        h_stop = re.search(r"^#{1,4}\s", tail, re.MULTILINE)
        h_idx = h_stop.start() if h_stop else len(tail)
        # Stop at next inline (mandatory) bold marker
        b_stop = re.search(r"^\*\*[^*]+\((?:mandatory|MANDATORY)", tail, re.MULTILINE)
        b_idx = b_stop.start() if b_stop else len(tail)
        body = tail[: min(h_idx, b_idx)]
        sections.append({
            "heading": title,
            "body": body,
            "line": line_no,
        })

    return sections


def _heading_keywords(heading: str) -> set[str]:
    """Token set from a heading for fuzzy xref matching against commands/*.md."""
    h = heading.lower()
    # Strip parenthetical suffixes and common filler words
    h = re.sub(r"\([^)]*\)", " ", h)
    h = re.sub(r"[—–\-:,\.\(\)\[\]]", " ", h)
    tokens = {t for t in re.split(r"\s+", h) if len(t) >= 4}
    stop = {"rule", "rules", "must", "when", "head", "coach", "before", "after"}
    return tokens - stop


def check_policy_workflow_coverage() -> list[dict]:
    """POLICY_COVERAGE — surface MANDATORY policies in framework/CLAUDE.md
    that lack a verifiable enforcement anchor in code or a /command workflow.

    Drift incident anchor: the "Daily balance rotation (mandatory)" in
    CLAUDE.md had no code path and no mention in `commands/training.md` —
    consequence: the coach skipped the balance unit. This check catches
    such sections early.
    """
    findings: list[dict] = []

    claude_path = FRAMEWORK_ROOT / "CLAUDE.md"
    text = _read(claude_path)
    if not text:
        return findings

    sections = _extract_mandatory_sections(text)

    # Pre-load all commands/*.md once
    commands_dir = FRAMEWORK_ROOT / "commands"
    command_docs: dict[str, str] = {}
    if commands_dir.is_dir():
        for f in commands_dir.glob("*.md"):
            command_docs[f.name] = _read(f).lower()

    for section in sections:
        body = section["body"]
        body_lower = body.lower()

        # 1. Code anchor?
        has_code = any(re.search(p, body, re.IGNORECASE) for p in _CODE_ANCHOR_PATTERNS)

        # 2. Policy-Only-Marker?
        is_policy_only = any(re.search(p, body_lower) for p in _POLICY_ONLY_PATTERNS)

        # 3. Workflow-Xref?
        kw = _heading_keywords(section["heading"])
        has_workflow_xref = False
        matched_cmd: str | None = None
        if kw:
            for cmd_name, cmd_text in command_docs.items():
                # Match if >= 2 distinctive keywords appear in the same command doc
                hits = sum(1 for t in kw if t in cmd_text)
                if hits >= 2:
                    has_workflow_xref = True
                    matched_cmd = cmd_name
                    break

        if has_code or is_policy_only or has_workflow_xref:
            continue

        # Drift candidate.
        findings.append(_finding(
            HIGH,
            "policy_coverage_drift",
            "framework/CLAUDE.md",
            source_line=section["line"],
            evidence=f"(mandatory) section '{section['heading']}' without code anchor, "
                     f"workflow xref, or policy-only marker",
            canonical_source="framework/CLAUDE.md",
            suggested_action="add_enforcement_anchor",
            fix_hint=(
                "Choose a path: (a) Code anchor — name a function/script in the "
                "body description (e.g. `enforced by push_workouts.py::_warn_on_xxx`). "
                "(b) Workflow xref — corresponding `commands/*.md` file mentions "
                "the section with >=2 keywords. (c) Policy-only — "
                "explicit marker like 'head-coach judgment' in the body, "
                "when no mechanisation is possible."
            ),
            description=(
                f"`{section['heading']}` is marked (mandatory) but "
                "neither a concrete code path nor a workflow doc xref is "
                "discoverable. This is the drift class that caused the "
                "balance unit to be silently dropped."
            ),
        ))

    return findings


CHECK_MAP = {
    "HR_ZONES": ("check_hr_zones", True),       # online
    "ORPHAN_MUSCLES": ("check_orphan_muscles", False),
    "UNMAPPED": ("check_unmapped_exercises", False),
    "NOTE_DRIFT": ("check_note_vs_static", True),
    "SHOES": ("check_strava_shoes", True),
    "HARDCODED": ("check_hardcoded_restrictions", False),
    "DELOAD": ("check_deload_consistency", False),
    "CONFIG_DRIFT": ("check_config_drift", False),
    "LOG_VS_HISTORY": ("check_log_vs_history", True),  # online (braucht activities)
    "PROGRESSION_OVERSHOOT": ("check_progression_overshoot", False),
    "OVERRIDE_DRIFT": ("check_override_drift", False),
    "PROMPT_DRIFT": ("check_prompt_drift", False),
    "POLICY_COVERAGE": ("check_policy_workflow_coverage", False),
}


def run_audit(offline: bool, only: str | None) -> dict[str, Any]:
    online_data: dict[str, Any] = {}
    if not offline:
        online_data = asyncio.run(_fetch_online())

    raw_findings: list[dict] = []
    selected = [only] if only else list(CHECK_MAP.keys())
    for name in selected:
        if name not in CHECK_MAP:
            continue
        fn_name, needs_online = CHECK_MAP[name]
        if needs_online and offline:
            continue
        try:
            if name == "HR_ZONES":
                results = check_hr_zones(online_data.get("athlete_settings"))
            elif name == "ORPHAN_MUSCLES":
                results = check_orphan_muscles()
            elif name == "UNMAPPED":
                results = check_unmapped_exercises()
            elif name == "NOTE_DRIFT":
                results = check_note_vs_static(online_data.get("notes"))
            elif name == "SHOES":
                results = check_strava_shoes(online_data.get("shoes"))
            elif name == "HARDCODED":
                results = check_hardcoded_restrictions()
            elif name == "DELOAD":
                results = check_deload_consistency()
            elif name == "CONFIG_DRIFT":
                results = check_config_drift()
            elif name == "LOG_VS_HISTORY":
                results = check_log_vs_history(online_data.get("activities"))
            elif name == "PROGRESSION_OVERSHOOT":
                results = check_progression_overshoot()
            elif name == "OVERRIDE_DRIFT":
                results = check_override_drift()
            elif name == "PROMPT_DRIFT":
                results = check_prompt_drift()
            elif name == "POLICY_COVERAGE":
                results = check_policy_workflow_coverage()
            else:
                results = []
            raw_findings.extend(results)
        except Exception as e:
            logger.exception("check %s failed", name)
            raw_findings.append(_finding(
                LOW, "check_error", f"scripts/audit_consistency.py::{name}",
                evidence=str(e),
                description=f"Check {name} ist fehlgeschlagen — manuell verifizieren",
            ))

    # IDs vergeben
    for i, f in enumerate(raw_findings, 1):
        f["id"] = f"F{i:03d}"

    summary = {
        "high": sum(1 for f in raw_findings if f["severity"] == HIGH),
        "medium": sum(1 for f in raw_findings if f["severity"] == MEDIUM),
        "low": sum(1 for f in raw_findings if f["severity"] == LOW),
        "total": len(raw_findings),
    }

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "online": not offline,
        "checks_run": [n for n in selected if n in CHECK_MAP and (not CHECK_MAP[n][1] or not offline)],
        "online_error": online_data.get("error"),
        "summary": summary,
        "findings": raw_findings,
    }


def _human_summary(report: dict) -> str:
    lines = [
        f"Audit {report['generated_at']} — online={report['online']}",
        f"  HIGH: {report['summary']['high']} | MEDIUM: {report['summary']['medium']} | LOW: {report['summary']['low']} | total: {report['summary']['total']}",
    ]
    if report.get("online_error"):
        lines.append(f"  ⚠ online-Fehler: {report['online_error']}")
    by_cat: dict[str, int] = {}
    for f in report["findings"]:
        by_cat[f["category"]] = by_cat.get(f["category"], 0) + 1
    if by_cat:
        lines.append("\nCategories:")
        for cat, n in sorted(by_cat.items(), key=lambda x: -x[1]):
            lines.append(f"  {n:3d}  {cat}")
    lines.append("\nDetails: use --json for full findings")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0] if __doc__ else "")
    parser.add_argument("--offline", action="store_true", help="Skip intervals.icu + Strava")
    parser.add_argument("--human", action="store_true", help="Readable summary instead of JSON")
    parser.add_argument("--check", choices=list(CHECK_MAP.keys()), help="Run a single check only")
    parser.add_argument("--log-level", default="WARNING")
    args = parser.parse_args()

    logging.basicConfig(level=args.log_level, format="%(levelname)s %(name)s: %(message)s")

    report = run_audit(offline=args.offline, only=args.check)
    if args.human:
        print(_human_summary(report))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
