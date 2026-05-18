"""Defensive escaping for text from external sources before injection into prompts.

External text — athlete notes from intervals.icu, activity descriptions from
Strava/Garmin, exercise descriptions parsed from workout files — can contain
markdown control characters, format-string placeholders ({...}), or even
instructions that look like prompt directives (`# system:`, etc.).

This module neutralises the most common prompt-injection vectors while
preserving the *meaning* of the text (the athlete can still read it). It is
NOT a hardening layer against an active adversary — it is a hygiene step that
makes accidental or low-effort injection ineffective.

See SECURITY.md for the threat model and what we explicitly do *not* defend
against.
"""

from __future__ import annotations

_ESCAPE_CHARS = ("`", "{", "}", "<", ">")


def escape_for_prompt(text: str | None, max_len: int = 200) -> str:
    """Return ``text`` made safe for inclusion in an LLM prompt.

    Operations applied (in order):
      1. ``None`` → ``""``
      2. Truncate to ``max_len`` characters
      3. Backslash-escape the characters in ``_ESCAPE_CHARS`` so they cannot
         start markdown code-fences, format-string placeholders, or HTML/XML
         pseudo-tags
      4. Strip leading ``#`` characters from each line (defangs accidental
         "# system:" / "# user:" markdown headings without losing the words)

    The result is suitable for concatenation into a prompt template. It is
    NOT a substitute for putting external text into a structured field
    (when a structured field is available, prefer that).
    """
    if not text:
        return ""

    text = text[:max_len]
    for ch in _ESCAPE_CHARS:
        text = text.replace(ch, f"\\{ch}")

    cleaned_lines: list[str] = []
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#"):
            cleaned_lines.append(stripped.lstrip("#").lstrip())
        else:
            cleaned_lines.append(line)
    return "\n".join(cleaned_lines)
