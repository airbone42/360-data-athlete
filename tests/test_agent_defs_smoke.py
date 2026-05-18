"""Smoke tests for the plugin agent definitions and slash commands."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
AGENTS_DIR = PLUGIN_ROOT / "agents"
COMMANDS_DIR = PLUGIN_ROOT / "commands"
README = PLUGIN_ROOT / "README.md"

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


def _parse_frontmatter(text: str) -> dict[str, str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    block = match.group(1)
    out: dict[str, str] = {}
    for line in block.splitlines():
        if ":" in line and not line.startswith(" "):
            key, _, value = line.partition(":")
            out[key.strip()] = value.strip()
    return out


@pytest.mark.parametrize("agent_path", sorted(AGENTS_DIR.glob("*.md")))
def test_agent_has_valid_frontmatter(agent_path: Path):
    text = agent_path.read_text(encoding="utf-8")
    fm = _parse_frontmatter(text)
    assert fm, f"{agent_path.name}: missing or malformed frontmatter"
    assert "name" in fm, f"{agent_path.name}: frontmatter missing 'name'"
    assert "description" in fm, f"{agent_path.name}: frontmatter missing 'description'"
    # name in frontmatter must match filename
    assert fm["name"] == agent_path.stem, (
        f"{agent_path.name}: frontmatter name '{fm['name']}' "
        f"does not match filename stem '{agent_path.stem}'"
    )


@pytest.mark.parametrize("agent_path", sorted(AGENTS_DIR.glob("*.md")))
def test_agent_body_non_empty(agent_path: Path):
    text = agent_path.read_text(encoding="utf-8")
    # Strip frontmatter
    body = FRONTMATTER_RE.sub("", text, count=1).strip()
    assert len(body) > 100, (
        f"{agent_path.name}: body looks empty after frontmatter ({len(body)} chars)"
    )


@pytest.mark.parametrize("command_path", sorted(COMMANDS_DIR.glob("*.md")))
def test_command_has_h1(command_path: Path):
    text = command_path.read_text(encoding="utf-8")
    first_line = text.splitlines()[0] if text else ""
    assert first_line.startswith("# "), (
        f"{command_path.name}: should open with an H1 (got: {first_line!r})"
    )


def test_readme_references_main_slash_commands():
    """README must visibly advertise the slash commands the plugin exposes."""
    assert README.exists()
    content = README.read_text(encoding="utf-8")
    for cmd in ("training", "analyse", "wellness", "muscleoverview", "audit"):
        # Either bare or namespaced reference is fine
        assert (
            f"/{cmd}" in content or f"aicoach-framework:{cmd}" in content
        ), f"README does not reference /{cmd}"


def test_readme_carries_clinical_disclaimer():
    """README must keep the EU MDR / clinical-consultant legal banner visible."""
    content = README.read_text(encoding="utf-8").lower()
    assert "eu mdr" in content, "README missing EU MDR jurisdiction note"
    assert "physio-consultant" in content or "clinical-consultant" in content, (
        "README does not name the clinical consultant agents in the disclaimer"
    )
