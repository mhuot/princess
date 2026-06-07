#!/usr/bin/env python3
"""
Tests for the in-memory logging buffer and its HTTP endpoints.

Copyright 2026 Mike Huot

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0
"""

import logging

from fastapi.testclient import TestClient

from princess.logging_config import (
    LOG_BUFFER,
    RingBufferHandler,
    room_logger,
    setup_logging,
)
from princess.server import app


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
    client = TestClient(app)
    res = client.get("/api/logs")
    assert res.status_code == 200
    body = res.json()
    assert body["capacity"] == LOG_BUFFER.capacity
    lines = [e["line"] for e in body["entries"]]
    assert any("princess-test-first" in line for line in lines)
    assert any("princess-test-second" in line for line in lines)


def test_api_logs_since_cursor_returns_only_new():
    setup_logging()
    LOG_BUFFER.clear()
    logging.getLogger("princess.test").info("alpha")
    client = TestClient(app)
    first = client.get("/api/logs").json()
    cursor = first["last_id"]
    logging.getLogger("princess.test").info("beta")
    second = client.get(f"/api/logs?since={cursor}").json()
    assert all(e["id"] > cursor for e in second["entries"])
    assert any("beta" in e["line"] for e in second["entries"])


def test_api_logs_download_is_attachment():
    setup_logging()
    LOG_BUFFER.clear()
    logging.getLogger("princess.test").info("download-me")
    client = TestClient(app)
    res = client.get("/api/logs/download")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/plain")
    assert 'attachment; filename="princess.log"' in res.headers["content-disposition"]
    assert "download-me" in res.text


def test_api_logs_download_empty_buffer_returns_placeholder():
    setup_logging()
    LOG_BUFFER.clear()
    client = TestClient(app)
    res = client.get("/api/logs/download")
    assert res.status_code == 200
    assert res.text.strip() != ""  # placeholder, not empty


def test_api_logs_delete_clears_buffer_and_logs_clear():
    setup_logging()
    LOG_BUFFER.clear()
    logging.getLogger("princess.test").info("about-to-be-cleared")
    client = TestClient(app)
    delete_res = client.delete("/api/logs")
    assert delete_res.status_code == 200
    after_lines = [e["line"] for e in LOG_BUFFER.snapshot()[0]]
    # After clear: pre-clear entries are gone; the clear acknowledgement line is in.
    assert not any("about-to-be-cleared" in ln for ln in after_lines)
    assert any("cleared" in ln.lower() for ln in after_lines)
