"""Smoke tests for the prompt YAMLs in `prompts/`."""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"
CONFIG_EXAMPLE = Path(__file__).resolve().parents[1] / "config.example"

PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")

REQUIRED_FIELDS = {"template"}
OPTIONAL_FIELDS = {"model", "temperature", "version", "max_tokens", "system"}


@pytest.mark.parametrize("yaml_path", sorted(PROMPTS_DIR.glob("*.yaml")))
def test_prompt_yaml_loads(yaml_path: Path):
    """Every prompt YAML must parse and carry the required fields."""
    with yaml_path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    assert isinstance(data, dict), f"{yaml_path.name}: top level must be a mapping"
    missing = REQUIRED_FIELDS - data.keys()
    assert not missing, f"{yaml_path.name}: missing required fields {missing}"


@pytest.mark.parametrize("yaml_path", sorted(PROMPTS_DIR.glob("*.yaml")))
def test_prompt_yaml_template_is_string(yaml_path: Path):
    with yaml_path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    assert isinstance(data.get("template"), str), (
        f"{yaml_path.name}: template field must be a string"
    )
    assert data["template"].strip(), f"{yaml_path.name}: template is empty"


@pytest.mark.parametrize("yaml_path", sorted(PROMPTS_DIR.glob("*.yaml")))
def test_prompt_temperature_in_range(yaml_path: Path):
    with yaml_path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    temp = data.get("temperature")
    if temp is None:
        pytest.skip("temperature not set")
    assert 0.0 <= float(temp) <= 2.0, (
        f"{yaml_path.name}: temperature {temp} outside [0, 2]"
    )


def test_prompt_placeholders_have_some_referent():
    """Every placeholder in a prompt template should plausibly be resolved.

    We don't enforce a hard whitelist (context fields come from `fetch_context.py`
    and aren't statically introspectable), but we sanity-check that the prompts
    aren't full of typos like `{ctll}` instead of `{ctl}`.
    """
    known_aliases = {
        "hr_zones",
        "athlete_static",
        "athlete_status",
        "athlete_preferences",
        "training_paradigms",
        "training_rules_planner",
        "training_rules_endurance",
        "training_rules_strength",
        "exercise_progressions",
        "exercise_checklist",
        "competition_plan",
        "equipment",
        "muscle_db",
        "recovery_protocol",
        "balance_pool",
        "context",
        "wellness",
        "directive",
        "type_history",
        "weather",
        "today",
        "date",
        "athlete_feedback",
    }

    suspect = []
    for yaml_path in sorted(PROMPTS_DIR.glob("*.yaml")):
        with yaml_path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        template = data.get("template", "")
        for placeholder in set(PLACEHOLDER_RE.findall(template)):
            if placeholder not in known_aliases and not placeholder.startswith("config_"):
                # collect — we just want a coarse signal, don't fail the suite
                suspect.append((yaml_path.name, placeholder))

    # Allow up to 30 unknown placeholders globally — context fields are dynamic.
    # Above that suggests structural drift.
    assert len(suspect) <= 30, (
        f"Too many unknown placeholders ({len(suspect)}). Drift likely. "
        f"First 10: {suspect[:10]}"
    )
