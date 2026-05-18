"""Loader for athlete/training configuration Markdown files.

Resolution: looks first in CONFIG_DIR (athlete-specific configs), then in
CONFIG_FALLBACK (framework defaults under config.example/). This allows the
public framework to ship with a demo athlete while a private wrapper
overrides individual files.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from app.utils.paths import CONFIG_DIR, CONFIG_FALLBACK

# Files in the config dirs that are documentation, not athlete config —
# `load_all_configs()` skips them so they don't leak into the merged dict
# (and accidentally become a prompt placeholder via {README}, etc.).
_NON_CONFIG_STEMS = frozenset({"README", "readme"})


def _resolve(name: str) -> Path:
    primary = CONFIG_DIR / f"{name}.md"
    if primary.exists():
        return primary
    fallback = CONFIG_FALLBACK / f"{name}.md"
    if fallback.exists():
        return fallback
    raise FileNotFoundError(
        f"Config file not found: tried {primary} and {fallback}"
    )


@lru_cache(maxsize=None)
def load_config(name: str) -> str:
    """Read {name}.md from CONFIG_DIR (with CONFIG_FALLBACK) and return content (cached)."""
    return _resolve(name).read_text(encoding="utf-8").strip()


def load_all_configs() -> dict[str, str]:
    """Return all *.md configs as a dict keyed by filename stem.

    Merges CONFIG_FALLBACK and CONFIG_DIR: athlete-specific files in
    CONFIG_DIR override framework defaults with the same name.

    Only configs explicitly referenced as {key} in a prompt template are
    actually injected — load_all_configs() itself adds no context overhead.
    """
    out: dict[str, str] = {}
    if CONFIG_FALLBACK.exists():
        for p in sorted(CONFIG_FALLBACK.glob("*.md")):
            if p.stem in _NON_CONFIG_STEMS:
                continue
            out[p.stem] = load_config(p.stem)
    if CONFIG_DIR.exists():
        for p in sorted(CONFIG_DIR.glob("*.md")):
            if p.stem in _NON_CONFIG_STEMS:
                continue
            out[p.stem] = load_config(p.stem)
    return out


def reload_configs() -> None:
    """Clear all config and prompt caches so next access re-reads from disk."""
    from app.utils.prompt_loader import load_prompt
    load_config.cache_clear()
    load_prompt.cache_clear()
