"""Error reporter — fire-and-forget, never raises.

Two transports:
    ALERT_COMMAND set   — the alert text goes to this command on stdin (split with
                          shlex, no shell). Lets a wrapper route alerts to its own
                          channel (inbox app, mail, chat webhook). Telegram is not used.
    otherwise           — Telegram Bot-API (TELEGRAM_BOT_ACCESS_TOKEN + chat id).

Public API:
    notify_error(msg, ctx) — send an alert message
    alert_on_failure       — decorator: wrap main() and call notify_error on crash
"""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import subprocess
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
_COMMAND_TIMEOUT_SEC = 30

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


def _resolve_command() -> list[str] | None:
    raw = os.environ.get("ALERT_COMMAND") or settings.alert_command
    try:
        argv = shlex.split(raw) if raw else []
    except ValueError as exc:
        print(f"[alerts] ALERT_COMMAND unparsable ({exc}) — falling back to Telegram", file=sys.stderr)
        return None
    return argv or None


def _send_command(argv: list[str], body: str) -> None:
    res = subprocess.run(argv, input=body, text=True, capture_output=True,
                         timeout=_COMMAND_TIMEOUT_SEC, check=False)
    if res.returncode != 0:
        print(f"[alerts] ALERT_COMMAND rc={res.returncode}: {res.stderr.strip()[-300:]}", file=sys.stderr)


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
    """Send an error alert via ALERT_COMMAND or the Telegram Bot-API. Never raises."""
    try:
        body = f"⚠️ Technischer Fehler: {msg}"
        if ctx:
            ctx_lines = "\n".join(f"  {k}: {v}" for k, v in ctx.items())
            body += f"\n\n{ctx_lines}"
        msg_hash = hashlib.sha1(body.encode()).hexdigest()[:12]
        if _is_duplicate(msg_hash):
            return
        argv = _resolve_command()
        if argv:
            _send_command(argv, body)
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
    and Ctrl+C should not trigger alerts.
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
