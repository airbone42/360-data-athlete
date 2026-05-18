"""Telegram error-reporter — fire-and-forget, never raises.

Public API:
    notify_error(msg, ctx) — send an alert message directly to Telegram Bot-API
    alert_on_failure       — decorator: wrap main() and call notify_error on crash
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import traceback
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Any

import httpx

from app.config import settings

_DEDUP_FILE = Path("/tmp/coach_alerts_last.json")
_DEDUP_WINDOW_SEC = 300  # 5 min — same error within this window is suppressed

# Optional path to a separate Telegram-plugin .env file (overrides pydantic-settings).
# When TELEGRAM_PLUGIN_ENV_PATH is set and the file is readable, TELEGRAM_BOT_TOKEN
# is parsed from there before falling back to pydantic-settings. No default path is
# assumed — wrappers that ship a Telegram integration at a fixed location must set
# the env var explicitly.
_PLUGIN_ENV_RAW = os.environ.get("TELEGRAM_PLUGIN_ENV_PATH")
_PLUGIN_ENV: Path | None = Path(_PLUGIN_ENV_RAW) if _PLUGIN_ENV_RAW else None


def _resolve_token() -> str | None:
    if _PLUGIN_ENV is not None and _PLUGIN_ENV.exists():
        for line in _PLUGIN_ENV.read_text().splitlines():
            if line.startswith("TELEGRAM_BOT_TOKEN="):
                tok = line.split("=", 1)[1].strip().strip('"')
                if tok:
                    return tok
    elif _PLUGIN_ENV_RAW:
        print(
            f"[alerts] TELEGRAM_PLUGIN_ENV_PATH={_PLUGIN_ENV_RAW} not found — "
            "falling back to pydantic-settings",
            file=sys.stderr,
        )
    tok = settings.telegram_bot_access_token
    return tok or None


def _resolve_chat_id() -> str | None:
    return settings.telegram_allowed_user_ids or settings.telegram_chat_id or None


def _is_duplicate(msg_hash: str) -> bool:
    now = time.time()
    try:
        data: dict[str, float] = json.loads(_DEDUP_FILE.read_text()) if _DEDUP_FILE.exists() else {}
    except Exception:
        data = {}
    if now - data.get(msg_hash, 0) < _DEDUP_WINDOW_SEC:
        return True
    data[msg_hash] = now
    data = {k: v for k, v in data.items() if now - v < _DEDUP_WINDOW_SEC * 4}
    try:
        _DEDUP_FILE.write_text(json.dumps(data))
    except Exception:
        pass
    return False


def notify_error(msg: str, ctx: dict[str, Any] | None = None) -> None:
    """Send an error alert via Telegram Bot-API. Never raises."""
    try:
        body = f"⚠️ Technischer Fehler: {msg}"
        if ctx:
            ctx_lines = "\n".join(f"  {k}: {v}" for k, v in ctx.items())
            body += f"\n\n{ctx_lines}"
        msg_hash = hashlib.sha1(body.encode()).hexdigest()[:12]
        if _is_duplicate(msg_hash):
            return
        token = _resolve_token()
        if not token:
            print(f"[alerts] no token — drop alert: {msg}", file=sys.stderr)
            return
        chat_id = _resolve_chat_id()
        if not chat_id:
            print(f"[alerts] no chat_id — drop alert: {msg}", file=sys.stderr)
            return
        httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": body[:4000]},
            timeout=5.0,
        )
    except Exception as exc:
        print(f"[alerts] send failed: {exc}", file=sys.stderr)


def alert_on_failure(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator: on unhandled Exception call notify_error and re-raise.

    SystemExit and KeyboardInterrupt are intentionally not caught — argparse errors
    and Ctrl+C should not trigger Telegram alerts.
    """
    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return fn(*args, **kwargs)
        except (SystemExit, KeyboardInterrupt):
            raise
        except BrokenPipeError:
            try:
                sys.stdout.close()
            except Exception:
                pass
            sys.exit(0)
        except Exception as exc:
            script = Path(sys.argv[0]).name if sys.argv and sys.argv[0] else fn.__name__
            tb_lines = traceback.format_exc().strip().splitlines()
            tb_snippet = " | ".join(tb_lines[-3:])
            notify_error(
                f"{script} abgebrochen",
                ctx={
                    "exception": f"{type(exc).__name__}: {exc}",
                    "traceback": tb_snippet,
                },
            )
            raise

    return wrapper
