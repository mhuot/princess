#!/usr/bin/env python3
"""
Tests for opt-in rotating JSONL file logging in ``princess.logging_config``.

Copyright 2026 Mike Huot

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0
"""

from __future__ import annotations

import json
import logging
import logging.handlers
from pathlib import Path

import pytest

from princess.logging_config import (
    JsonLineFormatter,
    LOG_BUFFER,
    _room_code_from_logger,
    setup_logging,
)


def _reset_logging() -> None:
    """Detach any handlers added by prior tests so setup_logging() reruns clean."""
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
        # Close file handlers so the tmp_path cleanup does not race the OS.
        try:
            handler.close()
        except Exception:  # pylint: disable=broad-exception-caught
            pass
    if hasattr(root, "_princess_configured"):
        delattr(root, "_princess_configured")
    # The module-level LOG_BUFFER singleton needs to be re-attached on the next
    # setup_logging() call; reset its formatter so the next attach re-applies.
    LOG_BUFFER.setFormatter(None)


@pytest.fixture(autouse=True)
def _restore_logging():
    yield
    _reset_logging()
    setup_logging()


def test_room_code_from_logger_parses_room_prefix():
    assert _room_code_from_logger("princess.room.AB12") == "AB12"
    assert _room_code_from_logger("princess.server") is None
    assert _room_code_from_logger("princess.room.") is None


def test_json_line_formatter_emits_required_fields():
    formatter = JsonLineFormatter()
    record = logging.LogRecord(
        name="princess.room.WXYZ",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello %s",
        args=("world",),
        exc_info=None,
    )
    payload = json.loads(formatter.format(record))
    assert payload["level"] == "INFO"
    assert payload["logger"] == "princess.room.WXYZ"
    assert payload["message"] == "hello world"
    assert payload["room"] == "WXYZ"
    assert isinstance(payload["ts"], str)


def test_no_file_handler_when_env_var_unset(monkeypatch):
    monkeypatch.delenv("PRINCESS_LOG_PATH", raising=False)
    _reset_logging()
    setup_logging()
    root = logging.getLogger()
    file_handlers = [
        h for h in root.handlers if isinstance(h, logging.handlers.RotatingFileHandler)
    ]
    assert file_handlers == []


def test_file_handler_attached_when_env_var_set(monkeypatch, tmp_path):
    log_path = tmp_path / "princess.log"
    monkeypatch.setenv("PRINCESS_LOG_PATH", str(log_path))
    _reset_logging()
    setup_logging()
    logging.getLogger("princess.test").info("hello-file")
    # Flush to make the line visible without waiting.
    for handler in logging.getLogger().handlers:
        handler.flush()
    assert log_path.exists()
    lines = [ln for ln in log_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert lines, "expected at least one JSON line in the file"
    matching = [json.loads(ln) for ln in lines if "hello-file" in ln]
    assert matching, "expected the emitted message to appear in the file"
    payload = matching[-1]
    assert payload["level"] == "INFO"
    assert payload["logger"] == "princess.test"
    assert payload["message"] == "hello-file"
    assert payload["room"] is None
    assert isinstance(payload["ts"], str)


def test_file_handler_records_room_code(monkeypatch, tmp_path):
    log_path = tmp_path / "princess.log"
    monkeypatch.setenv("PRINCESS_LOG_PATH", str(log_path))
    _reset_logging()
    setup_logging()
    logging.getLogger("princess.room.AB12").info("room-msg")
    for handler in logging.getLogger().handlers:
        handler.flush()
    lines = [ln for ln in log_path.read_text(encoding="utf-8").splitlines() if "room-msg" in ln]
    assert lines, "expected room message in file"
    payload = json.loads(lines[-1])
    assert payload["room"] == "AB12"


def test_file_handler_records_null_room_for_non_room_logger(monkeypatch, tmp_path):
    log_path = tmp_path / "princess.log"
    monkeypatch.setenv("PRINCESS_LOG_PATH", str(log_path))
    _reset_logging()
    setup_logging()
    logging.getLogger("princess").info("plain-msg")
    for handler in logging.getLogger().handlers:
        handler.flush()
    lines = [ln for ln in log_path.read_text(encoding="utf-8").splitlines() if "plain-msg" in ln]
    assert lines, "expected plain message in file"
    payload = json.loads(lines[-1])
    assert payload["room"] is None


def test_file_handler_includes_exc_info(monkeypatch, tmp_path):
    log_path = tmp_path / "princess.log"
    monkeypatch.setenv("PRINCESS_LOG_PATH", str(log_path))
    _reset_logging()
    setup_logging()
    logger = logging.getLogger("princess.test")
    try:
        raise RuntimeError("kaboom")
    except RuntimeError:
        logger.exception("boom")
    for handler in logging.getLogger().handlers:
        handler.flush()
    lines = [ln for ln in log_path.read_text(encoding="utf-8").splitlines() if "boom" in ln]
    assert lines, "expected exception line in file"
    payload = json.loads(lines[-1])
    assert "exc_info" in payload
    assert "Traceback" in payload["exc_info"]
    assert "RuntimeError" in payload["exc_info"]


def test_unwritable_path_fails_open(monkeypatch, tmp_path):
    # Point at a path under a directory that does not exist.
    bad_path = tmp_path / "does-not-exist" / "princess.log"
    monkeypatch.setenv("PRINCESS_LOG_PATH", str(bad_path))
    _reset_logging()
    setup_logging()  # must not raise
    root = logging.getLogger()
    file_handlers = [
        h for h in root.handlers if isinstance(h, logging.handlers.RotatingFileHandler)
    ]
    assert file_handlers == []
    assert not Path(bad_path).exists()


def test_empty_env_var_is_treated_as_unset(monkeypatch):
    monkeypatch.setenv("PRINCESS_LOG_PATH", "")
    _reset_logging()
    setup_logging()
    root = logging.getLogger()
    file_handlers = [
        h for h in root.handlers if isinstance(h, logging.handlers.RotatingFileHandler)
    ]
    assert file_handlers == []
