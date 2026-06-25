#!/usr/bin/env python3
"""
Tests for the in-memory logging buffer and its HTTP endpoints.

Copyright 2026 Mike Huot

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0
"""

import asyncio
import logging
from unittest.mock import MagicMock

from fastapi import HTTPException as FastAPIHTTPException
from fastapi.testclient import TestClient

from princess.logging_config import (
    LOG_BUFFER,
    RingBufferHandler,
    redact_pid,
    room_logger,
    setup_logging,
)
from princess.server import app, require_localhost


def _loopback_client() -> TestClient:
    """TestClient that bypasses the localhost guard (simulates operator access)."""
    app.dependency_overrides[require_localhost] = lambda: None
    client = TestClient(app)
    return client


def _reset_overrides() -> None:
    app.dependency_overrides.clear()


def _record(
    level: int = logging.INFO, name: str = "princess.test", msg: str = "hello"
) -> logging.LogRecord:
    return logging.LogRecord(
        name=name,
        level=level,
        pathname=__file__,
        lineno=10,
        msg=msg,
        args=(),
        exc_info=None,
    )


def test_ring_buffer_appends_and_caps_at_capacity():
    buf = RingBufferHandler(capacity=3)
    buf.setFormatter(logging.Formatter("%(message)s"))
    for i in range(5):
        buf.emit(_record(msg=f"line-{i}"))
    entries, last_id = buf.snapshot()
    # Oldest two dropped; ids 3, 4, 5 remain (counter starts at 1).
    assert [e["line"] for e in entries] == ["line-2", "line-3", "line-4"]
    assert last_id == entries[-1]["id"]


def test_ring_buffer_snapshot_since_cursor():
    buf = RingBufferHandler(capacity=10)
    buf.setFormatter(logging.Formatter("%(message)s"))
    for i in range(5):
        buf.emit(_record(msg=f"line-{i}"))
    entries, last_id = buf.snapshot(since=2)
    assert [e["id"] for e in entries] == [3, 4, 5]
    assert last_id == 5
    assert all(e["id"] > 2 for e in entries)


def test_ring_buffer_snapshot_limit_clamps_to_most_recent():
    buf = RingBufferHandler(capacity=10)
    buf.setFormatter(logging.Formatter("%(message)s"))
    for i in range(8):
        buf.emit(_record(msg=f"line-{i}"))
    entries, last_id = buf.snapshot(limit=3)
    assert [e["line"] for e in entries] == ["line-5", "line-6", "line-7"]
    assert last_id == entries[-1]["id"]


def test_ring_buffer_snapshot_when_empty():
    buf = RingBufferHandler(capacity=3)
    entries, last_id = buf.snapshot(since=42)
    assert entries == []
    assert last_id == 42  # passes the cursor through unchanged


def test_ring_buffer_dump_text_joins_lines():
    buf = RingBufferHandler(capacity=3)
    buf.setFormatter(logging.Formatter("%(message)s"))
    for i in range(2):
        buf.emit(_record(msg=f"line-{i}"))
    assert buf.dump_text() == "line-0\nline-1"


def test_ring_buffer_clear_empties_state():
    buf = RingBufferHandler(capacity=3)
    buf.setFormatter(logging.Formatter("%(message)s"))
    buf.emit(_record(msg="x"))
    buf.clear()
    entries, _ = buf.snapshot()
    assert entries == []


def test_setup_logging_is_idempotent():
    setup_logging()
    first_handler_count = len(logging.getLogger().handlers)
    setup_logging()
    assert len(logging.getLogger().handlers) == first_handler_count


def test_room_logger_namespaced_by_code():
    lg = room_logger("ABCD")
    assert lg.name == "princess.room.ABCD"


def test_api_logs_returns_recent_entries():
    setup_logging()
    LOG_BUFFER.clear()
    logging.getLogger("princess.test").info("princess-test-first")
    logging.getLogger("princess.test").info("princess-test-second")
    client = _loopback_client()
    try:
        res = client.get("/api/logs")
        assert res.status_code == 200
        body = res.json()
        assert body["capacity"] == LOG_BUFFER.capacity
        lines = [e["line"] for e in body["entries"]]
        assert any("princess-test-first" in line for line in lines)
        assert any("princess-test-second" in line for line in lines)
    finally:
        _reset_overrides()


def test_api_logs_since_cursor_returns_only_new():
    setup_logging()
    LOG_BUFFER.clear()
    logging.getLogger("princess.test").info("alpha")
    client = _loopback_client()
    try:
        first = client.get("/api/logs").json()
        cursor = first["last_id"]
        logging.getLogger("princess.test").info("beta")
        second = client.get(f"/api/logs?since={cursor}").json()
        assert all(e["id"] > cursor for e in second["entries"])
        assert any("beta" in e["line"] for e in second["entries"])
    finally:
        _reset_overrides()


def test_api_logs_download_is_attachment():
    setup_logging()
    LOG_BUFFER.clear()
    logging.getLogger("princess.test").info("download-me")
    client = _loopback_client()
    try:
        res = client.get("/api/logs/download")
        assert res.status_code == 200
        assert res.headers["content-type"].startswith("text/plain")
        assert 'attachment; filename="princess.log"' in res.headers["content-disposition"]
        assert "download-me" in res.text
    finally:
        _reset_overrides()


def test_api_logs_download_empty_buffer_returns_placeholder():
    setup_logging()
    LOG_BUFFER.clear()
    client = _loopback_client()
    try:
        res = client.get("/api/logs/download")
        assert res.status_code == 200
        assert res.text.strip() != ""  # placeholder, not empty
    finally:
        _reset_overrides()


def test_api_logs_delete_clears_buffer_and_logs_clear():
    setup_logging()
    LOG_BUFFER.clear()
    logging.getLogger("princess.test").info("about-to-be-cleared")
    client = _loopback_client()
    try:
        delete_res = client.delete("/api/logs")
        assert delete_res.status_code == 200
        after_lines = [e["line"] for e in LOG_BUFFER.snapshot()[0]]
        # After clear: pre-clear entries are gone; the clear acknowledgement line is in.
        assert not any("about-to-be-cleared" in ln for ln in after_lines)
        assert any("cleared" in ln.lower() for ln in after_lines)
    finally:
        _reset_overrides()


# --- redact_pid unit tests ---------------------------------------------------


def test_redact_pid_is_stable_within_process():
    raw = "abc123XY"
    assert redact_pid(raw) == redact_pid(raw)


def test_redact_pid_differs_from_raw():
    raw = "abc123XY"
    assert redact_pid(raw) != raw


def test_redact_pid_differs_for_different_inputs():
    assert redact_pid("aaa") != redact_pid("bbb")


def test_redact_pid_none_returns_placeholder():
    result = redact_pid(None)
    assert result == "--------"
    assert len(result) == 8


def test_redact_pid_empty_string_returns_placeholder():
    assert redact_pid("") == "--------"


def test_redact_pid_output_is_8_hex_chars():
    result = redact_pid("sometoken")
    assert len(result) == 8
    assert all(c in "0123456789abcdef" for c in result)


# --- pid-redaction integration test -----------------------------------------


def test_raw_pids_never_appear_in_log_buffer():
    """Create a room, join, add a bot — raw tokens must not appear in the buffer."""
    setup_logging()
    LOG_BUFFER.clear()

    client = TestClient(app)
    create_res = client.post("/api/rooms", json={"name": "Alice"}).json()
    host_pid = create_res["pid"]
    code = create_res["code"]

    join_res = client.post(f"/api/rooms/{code}/join", json={"name": "Bob"}).json()
    guest_pid = join_res["pid"]

    bot_res = client.post(f"/api/rooms/{code}/bot", json={"host_pid": host_pid}).json()
    assert bot_res.get("ok")

    buf = LOG_BUFFER.dump_text()
    assert host_pid not in buf, "raw host_pid leaked into log buffer"
    assert guest_pid not in buf, "raw guest_pid leaked into log buffer"


# --- localhost guard tests ---------------------------------------------------


def test_log_endpoints_return_403_for_non_loopback():
    """TestClient presents as 'testclient' host — non-loopback, so all log routes return 403."""
    setup_logging()
    client = TestClient(app)
    assert client.get("/api/logs").status_code == 403
    assert client.get("/api/logs/download").status_code == 403
    assert client.delete("/api/logs").status_code == 403


def test_log_endpoints_allow_loopback():
    """Loopback override allows all three endpoints."""
    setup_logging()
    LOG_BUFFER.clear()
    logging.getLogger("princess.test").info("loopback-check")
    client = _loopback_client()
    try:
        assert client.get("/api/logs").status_code == 200
        assert client.get("/api/logs/download").status_code == 200
        assert client.delete("/api/logs").status_code == 200
    finally:
        _reset_overrides()


def test_require_localhost_none_client_returns_403():
    """require_localhost must fail closed when request.client is None."""
    mock_request = MagicMock()
    mock_request.client = None

    async def _run():
        try:
            await require_localhost(mock_request)
            return False
        except FastAPIHTTPException as exc:
            return exc.status_code == 403

    assert asyncio.run(_run())
