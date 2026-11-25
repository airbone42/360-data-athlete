"""ALERT_COMMAND routes alerts to a command on stdin instead of Telegram."""
from __future__ import annotations

import sys

from app.utils import alerts


def _fresh(monkeypatch, tmp_path):
    monkeypatch.setattr(alerts, "_DEDUP_FILE", tmp_path / "dedup.json")


def test_command_receives_alert_and_telegram_is_not_used(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    out = tmp_path / "out.txt"
    script = tmp_path / "sink.py"
    script.write_text(f"import sys; open({str(out)!r}, 'w').write(sys.stdin.read())\n")
    monkeypatch.setenv("ALERT_COMMAND", f"{sys.executable} {script}")
    monkeypatch.setattr(alerts.httpx, "post", lambda *a, **k: (_ for _ in ()).throw(AssertionError("telegram")))
    alerts.notify_error("push_workouts.py abgebrochen", {"exception": "ValueError: x"})
    text = out.read_text()
    assert text.startswith("⚠️ Technischer Fehler: push_workouts.py abgebrochen")
    assert "exception: ValueError: x" in text


def test_failing_command_never_raises(monkeypatch, tmp_path, capsys):
    _fresh(monkeypatch, tmp_path)
    monkeypatch.setenv("ALERT_COMMAND", f"{sys.executable} -c 'import sys; sys.exit(3)'")
    alerts.notify_error("boom")
    assert "rc=3" in capsys.readouterr().err


def test_missing_command_never_raises(monkeypatch, tmp_path, capsys):
    _fresh(monkeypatch, tmp_path)
    monkeypatch.setenv("ALERT_COMMAND", str(tmp_path / "does-not-exist"))
    alerts.notify_error("boom")
    assert "send failed" in capsys.readouterr().err


def test_without_command_falls_back_to_telegram(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    monkeypatch.delenv("ALERT_COMMAND", raising=False)
    monkeypatch.setattr(alerts.settings, "alert_command", "")
    monkeypatch.setattr(alerts, "_resolve_token", lambda: "t")
    monkeypatch.setattr(alerts, "_resolve_chat_id", lambda: "1")
    sent = []
    monkeypatch.setattr(alerts.httpx, "post", lambda url, **k: sent.append((url, k["data"]["text"])))
    alerts.notify_error("boom")
    assert sent and sent[0][0].endswith("/sendMessage") and "boom" in sent[0][1]
