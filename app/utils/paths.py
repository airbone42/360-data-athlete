"""Central path resolution for the coach system.

The framework code (under app/, scripts/, prompts/) is portable: it can be
embedded as a submodule inside an athlete-specific wrapper repository.
Runtime data (config/, data/, cache/) lives in the wrapper, not in the
framework itself.

Resolution order:
    COACH_HOME   — wrapper root; defaults to FRAMEWORK_ROOT when running
                   the framework standalone (with config.example/ as default
                   athlete).
    CONFIG_DIR   — overrides $COACH_HOME/config
    DATA_DIR     — overrides $COACH_HOME/data
    CACHE_DIR    — overrides $COACH_HOME/cache (legacy var:
                   INTERVALS_CACHE_DIR still respected for backwards compat)

CONFIG_FALLBACK is always FRAMEWORK_ROOT/config.example and is used by
load_config() when a requested key is missing from CONFIG_DIR.
"""

from __future__ import annotations

import os
from pathlib import Path

FRAMEWORK_ROOT: Path = Path(__file__).resolve().parent.parent.parent
COACH_HOME: Path = Path(os.environ.get("COACH_HOME", FRAMEWORK_ROOT)).resolve()
CONFIG_DIR: Path = Path(os.environ.get("CONFIG_DIR", COACH_HOME / "config")).resolve()
DATA_DIR: Path = Path(os.environ.get("DATA_DIR", COACH_HOME / "data")).resolve()
CACHE_DIR: Path = Path(
    os.environ.get("CACHE_DIR")
    or os.environ.get("INTERVALS_CACHE_DIR")
    or (COACH_HOME / "cache")
).resolve()
PROMPTS_DIR: Path = (FRAMEWORK_ROOT / "prompts").resolve()
CONFIG_FALLBACK: Path = (FRAMEWORK_ROOT / "config.example").resolve()


def resolve_config(filename: str) -> Path:
    """Resolve a config file by filename, checking CONFIG_DIR then CONFIG_FALLBACK.

    Use for non-Markdown configs (JSON, YAML, etc.). For .md files, prefer
    load_config() from config_loader which returns the file contents.

    Raises FileNotFoundError if neither location contains the file.
    """
    primary = CONFIG_DIR / filename
    if primary.exists():
        return primary
    fallback = CONFIG_FALLBACK / filename
    if fallback.exists():
        return fallback
    raise FileNotFoundError(
        f"Config not found: tried {primary} and {fallback}"
    )
