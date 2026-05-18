"""Smoke tests for the Claude Code plugin manifest and marketplace entry."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = PLUGIN_ROOT / ".claude-plugin"

# Matches `python3 scripts/...` or `python scripts/...` — the bare form that
# only works when cwd == framework root. Plugin commands and agents must use
# `python3 "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/...` so they resolve correctly
# in both plugin mode (cwd = consumer session root) and standalone mode
# (cwd = framework root, variable unset, default `.` kicks in).
_BARE_SCRIPT_PATH = re.compile(r"python3?\s+scripts/")


def test_plugin_json_exists_and_parses():
    path = PLUGIN_DIR / "plugin.json"
    assert path.exists(), f"missing plugin manifest at {path}"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "name" in data, "plugin.json must declare a name"
    assert isinstance(data["name"], str) and data["name"], "name must be a non-empty string"


def test_marketplace_json_exists_and_parses():
    path = PLUGIN_DIR / "marketplace.json"
    assert path.exists(), f"missing marketplace manifest at {path}"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "name" in data, "marketplace.json must declare a name"
    assert "plugins" in data and isinstance(data["plugins"], list)
    assert any(p.get("name") for p in data["plugins"]), "no plugins listed"


def test_marketplace_lists_aicoach_framework():
    data = json.loads((PLUGIN_DIR / "marketplace.json").read_text(encoding="utf-8"))
    names = [p.get("name") for p in data["plugins"]]
    assert "aicoach-framework" in names, f"aicoach-framework not in {names}"


def test_agents_directory_populated():
    agents = PLUGIN_ROOT / "agents"
    assert agents.exists() and agents.is_dir()
    md_files = list(agents.glob("*.md"))
    assert len(md_files) >= 10, f"expected >=10 agents, got {len(md_files)}"


def test_commands_directory_populated():
    commands = PLUGIN_ROOT / "commands"
    assert commands.exists() and commands.is_dir()
    md_files = list(commands.glob("*.md"))
    assert len(md_files) >= 5, f"expected >=5 commands, got {len(md_files)}"


@pytest.mark.parametrize(
    "agent_name",
    [
        "planner",
        "specialist-endurance",
        "specialist-complementary",
        "specialist-ninja",
        "coach-analyst",
        "data-scientist",
        "mental-coach",
        "video-analyst",
        "plan-validator",
        "config-auditor",
        "config-fixer",
        "physio-consultant",
        "sports-ortho-consultant",
    ],
)
def test_expected_agent_present(agent_name: str):
    path = PLUGIN_ROOT / "agents" / f"{agent_name}.md"
    assert path.exists(), f"missing agent {agent_name}.md"
    content = path.read_text(encoding="utf-8")
    assert content.startswith("---"), f"{agent_name}.md missing frontmatter"
    assert f"name: {agent_name}" in content, f"{agent_name}.md frontmatter name mismatch"


@pytest.mark.parametrize(
    "command_name",
    ["training", "analyse", "wellness", "muscleoverview", "audit", "pull"],
)
def test_expected_command_present(command_name: str):
    path = PLUGIN_ROOT / "commands" / f"{command_name}.md"
    assert path.exists(), f"missing command {command_name}.md"


@pytest.mark.parametrize("subdir", ["commands", "agents"])
def test_no_bare_scripts_path_in_plugin_artifacts(subdir: str) -> None:
    """Plugin commands/agents must not call `python3 scripts/...` directly.

    In plugin mode the consumer's session cwd (NOT the plugin root) is what
    the shell sees, so a bare `scripts/foo.py` resolves against the wrong
    directory and fails with `No such file or directory`. Use
    `python3 "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/foo.py` instead — the
    bash default substitution keeps the line working in standalone mode
    too (variable unset → `.` → cwd = framework root).
    """
    root = PLUGIN_ROOT / subdir
    offenders: list[str] = []
    for md in sorted(root.glob("*.md")):
        for lineno, line in enumerate(
            md.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not _BARE_SCRIPT_PATH.search(line):
                continue
            if "CLAUDE_PLUGIN_ROOT" in line:
                continue
            offenders.append(f"{md.name}:{lineno}: {line.strip()}")
    assert not offenders, (
        "bare `python3 scripts/...` paths found in plugin artifacts — these "
        "break in plugin mode. Replace with "
        '`python3 "${CLAUDE_PLUGIN_ROOT:-.}"/scripts/...`:\n  '
        + "\n  ".join(offenders)
    )


def test_clinical_agents_carry_strong_disclaimer():
    """Physio + ortho consultant agents must carry the EU MDR / DE-AT-CH legal banner."""
    for name in ("physio-consultant", "sports-ortho-consultant"):
        content = (PLUGIN_ROOT / "agents" / f"{name}.md").read_text(encoding="utf-8")
        lower = content.lower()
        assert "not a medical practitioner" in lower or "not a licensed" in lower, (
            f"{name}: missing 'not a medical practitioner' disclaimer"
        )
        assert "eu mdr" in lower, f"{name}: missing EU MDR jurisdiction note"
