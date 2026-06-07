#!/usr/bin/env python3
"""
Logging setup for Princess Card Game.

Logs go to stdout and to an in-memory FIFO ring buffer (no filesystem).
The ring buffer is bounded so it can't grow without limit.

The browser fetches log lines via `/api/logs` and can download the full
buffer via `/api/logs/download`.

Call ``setup_logging()`` once at startup. Subsequent imports just call
``logging.getLogger(__name__)``.

Copyright 2026 Mike Huot

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0
"""

from __future__ import annotations

import collections
import itertools
import logging
import os
import sys
import threading

LOG_FORMAT = "%(asctime)s [%(levelname)-5s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

DEFAULT_BUFFER_SIZE = 2000


class RingBufferHandler(logging.Handler):
    """In-memory FIFO log handler. Drops oldest entries past ``capacity``."""

    def __init__(self, capacity: int = DEFAULT_BUFFER_SIZE) -> None:
        super().__init__(level=logging.DEBUG)
        self._lock = threading.Lock()
        self._counter = itertools.count(1)
        self._buffer: collections.deque[tuple[int, str]] = collections.deque(maxlen=capacity)

    @property
    def capacity(self) -> int:
        return self._buffer.maxlen or 0

    def emit(self, record: logging.LogRecord) -> None:
        try:
            line = self.format(record)
        except Exception:  # pylint: disable=broad-exception-caught
            self.handleError(record)
            return
        with self._lock:
            self._buffer.append((next(self._counter), line))

    def snapshot(self, since: int = 0, limit: int | None = None) -> tuple[list[dict], int]:
        """Return (entries, last_id). Each entry: {"id": int, "line": str}.

        ``since``: only include entries with id > since.
        ``limit``: cap returned entries to the most recent N (after the since filter).
        """
        with self._lock:
            items = [{"id": i, "line": ln} for i, ln in self._buffer if i > since]
        if limit and len(items) > limit:
            items = items[-limit:]
        last_id = items[-1]["id"] if items else since
        return items, last_id

    def dump_text(self) -> str:
        with self._lock:
            return "\n".join(line for _, line in self._buffer)

    def clear(self) -> None:
        with self._lock:
            self._buffer.clear()


# Singleton — modules can import this directly to read the buffer.
LOG_BUFFER = RingBufferHandler()


def setup_logging(level: str | int | None = None) -> None:
    """Configure root logging with stdout + in-memory ring buffer. Idempotent."""
    root = logging.getLogger()
    if getattr(root, "_princess_configured", False):
        return

    level_str = level if level is not None else os.environ.get("LOG_LEVEL", "INFO")
    if isinstance(level_str, str):
        resolved_level = getattr(logging, level_str.upper(), logging.INFO)
    else:
        resolved_level = level_str

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(resolved_level)
    console.setFormatter(formatter)

    LOG_BUFFER.setFormatter(formatter)

    root.setLevel(min(resolved_level, logging.DEBUG))
    root.addHandler(console)
    root.addHandler(LOG_BUFFER)
    root._princess_configured = True  # type: ignore[attr-defined]  # pylint: disable=protected-access

    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)

    logging.getLogger("princess").info(
        "logging initialized — level=%s buffer=%d entries (in-memory)",
        logging.getLevelName(resolved_level),
        LOG_BUFFER.capacity,
    )


def room_logger(code: str) -> logging.Logger:
    """Get a logger scoped to a specific room code."""
    return logging.getLogger(f"princess.room.{code}")
