#!/usr/bin/env python3
"""
Test-suite setup shared across all test modules.

Disables the per-IP HTTP rate limiter for the default session so existing
smoke tests (which hammer ``POST /api/rooms`` and friends in quick succession)
are not affected by the new quotas. Tests that need to exercise enforcement
clear the env var and rebuild the app under ``importlib.reload``.

Also provides a ``tmp_db`` fixture that binds the module-level ``REGISTRY``
to a per-test SQLite file inside ``tmp_path`` so persistence tests are fully
isolated from each other and from any local ``./princess.db``.

Copyright 2026 Mike Huot

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0
"""

import os

# Must be set before any test module imports ``princess.server``.
os.environ.setdefault("PRINCESS_RATE_LIMIT_DISABLED", "1")

# pylint: disable=wrong-import-position
import pytest

from princess import rooms as rooms_module


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """Bind ``princess.rooms.REGISTRY`` to a fresh per-test SQLite file.

    The fixture also clears the registry's in-memory ``_rooms`` so the test
    starts from an empty state. After the test, the connection is closed and
    the registry is restored to its pre-test connection (typically ``None``).
    """
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("PRINCESS_DB_PATH", str(db_path))

    prev_conn = rooms_module.REGISTRY._conn  # pylint: disable=protected-access
    prev_db_path = rooms_module.REGISTRY._db_path  # pylint: disable=protected-access
    prev_rooms = dict(rooms_module.REGISTRY._rooms)  # pylint: disable=protected-access
    rooms_module.REGISTRY._rooms.clear()  # pylint: disable=protected-access
    rooms_module.REGISTRY.attach_db(str(db_path))
    try:
        yield rooms_module.REGISTRY
    finally:
        conn = rooms_module.REGISTRY._conn  # pylint: disable=protected-access
        if conn is not None:
            conn.close()
        rooms_module.REGISTRY._conn = prev_conn  # pylint: disable=protected-access
        rooms_module.REGISTRY._db_path = prev_db_path  # pylint: disable=protected-access
        rooms_module.REGISTRY._rooms.clear()  # pylint: disable=protected-access
        rooms_module.REGISTRY._rooms.update(prev_rooms)  # pylint: disable=protected-access
