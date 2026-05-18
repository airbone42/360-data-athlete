"""Prompt loader for YAML-based prompt registry."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import yaml

from app.utils.config_loader import load_all_configs
from app.utils.paths import PROMPTS_DIR as _PROMPTS_DIR


@dataclass
class PromptConfig:
    template: str
    model: str
    temperature: float
    version: str
    response_format: str | None = None
    max_tokens: int | None = None


@lru_cache(maxsize=None)
def load_prompt(name: str) -> PromptConfig:
    """Load prompts/{name}.yaml and return PromptConfig."""
    path = _PROMPTS_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")

    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    meta = data.get("metadata", {})
    model = meta.get("model")
    temperature = meta.get("temperature")
    template = data.get("template")

    if not model:
        raise ValueError(f"Prompt '{name}': metadata.model is required")
    if temperature is None:
        raise ValueError(f"Prompt '{name}': metadata.temperature is required")
    if not template:
        raise ValueError(f"Prompt '{name}': template is required")

    # Resolve {config_key} placeholders from config/ markdown files
    class _SafeFormatMap(dict):
        def __missing__(self, key: str) -> str:
            return f"{{{key}}}"

    configs = load_all_configs()
    template = template.format_map(_SafeFormatMap(configs))

    return PromptConfig(
        template=template,
        model=model,
        temperature=float(temperature),
        version=meta.get("version", "0.0.0"),
        response_format=meta.get("response_format"),
        max_tokens=meta.get("max_tokens"),
    )
