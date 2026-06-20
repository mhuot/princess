#!/usr/bin/env python3
"""
Tests for the persistent global leaderboard.

Covers schema creation, name normalization, bump idempotency, bot exclusion,
SQLite error isolation, the read endpoint (sort + filter + cache + 400s),
and that an empty / no-DB deployment returns an empty list.

Copyright 2026 Mike Huot

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0
"""

# pytest passes fixtures by parameter name, which pylint reads as
# redefined-outer-name from the @fixture function above.
# pylint: disable=redefined-outer-name

from __future__ import annotations

import asyncio
import sqlite3

import pytest
from fastapi.testclient import TestClient

from princess import rooms as rooms_module
from princess import server as server_module
from princess.game import Game, Player
from princess.rooms import Room, RoomRegistry, Seat, _normalize_name
from princess.server import app

# --- normalization ----------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Alice", "alice"),
        ("ALICE", "alice"),
        ("  alice  ", "alice"),
        ("Alice  B", "alice b"),
        ("\talice\nB\t", "alice b"),
        ("alice b", "alice b"),
    ],
)
def test_normalize_name(raw, expected):
    assert _normalize_name(raw) == expected


# --- table creation ---------------------------------------------------------


def test_open_db_creates_leaderboard_table(tmp_path):
    db_path = tmp_path / "lb.db"
    registry = RoomRegistry(db_path=str(db_path))
    try:
        rows = list(
            registry._conn.execute(  # pylint: disable=protected-access
                "SELECT name FROM sqlite_master WHERE type='table' AND name='leaderboard'"
            )
        )
        assert rows, "leaderboard table not created"
        # Index too
        idx = list(
            registry._conn.execute(  # pylint: disable=protected-access
                "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_leaderboard_wins'"
            )
        )
        assert idx, "leaderboard wins index not created"
    finally:
        registry._conn.close()  # pylint: disable=protected-access


def test_table_preserved_across_restarts(tmp_path):
    db_path = tmp_path / "lb.db"
    r1 = RoomRegistry(db_path=str(db_path))
    asyncio.run(r1.bump_global_leaderboard(["pA"], {"pA": "Alice"}))
    r1._conn.close()  # pylint: disable=protected-access

    r2 = RoomRegistry(db_path=str(db_path))
    try:
        entries = r2.read_leaderboard(limit=10, sort="wins", min_rounds=0)
        assert len(entries) == 1
        assert entries[0]["display_name"] == "Alice"
        assert entries[0]["princess_wins"] == 1
    finally:
        r2._conn.close()  # pylint: disable=protected-access


# --- no-DB fast path --------------------------------------------------------


def test_no_db_bump_is_noop():
    registry = RoomRegistry(db_path=None)
    asyncio.run(registry.bump_global_leaderboard(["p1"], {"p1": "Alice"}))
    assert registry.read_leaderboard(limit=10, sort="wins", min_rounds=0) == []


# --- bumping --------------------------------------------------------------


def _bump(registry: RoomRegistry, order: list[str], names: dict[str, str]) -> None:
    asyncio.run(registry.bump_global_leaderboard(order, names))


def test_bump_winner_and_last_credited(tmp_path):
    registry = RoomRegistry(db_path=str(tmp_path / "lb.db"))
    try:
        _bump(registry, ["pA", "pB", "pC", "pD"], {"pA": "A", "pB": "B", "pC": "C", "pD": "D"})
        rows = {
            r["display_name"]: r
            for r in registry.read_leaderboard(limit=10, sort="wins", min_rounds=0)
        }
        assert rows["A"]["princess_wins"] == 1 and rows["A"]["last_places"] == 0
        assert rows["D"]["last_places"] == 1 and rows["D"]["princess_wins"] == 0
        for name in ("A", "B", "C", "D"):
            assert rows[name]["rounds_played"] == 1
    finally:
        registry._conn.close()  # pylint: disable=protected-access


def test_bump_aggregates_by_normalized_name(tmp_path):
    registry = RoomRegistry(db_path=str(tmp_path / "lb.db"))
    try:
        _bump(registry, ["p1"], {"p1": "Alice"})
        _bump(registry, ["p2"], {"p2": "ALICE"})
        _bump(registry, ["p3"], {"p3": "  alice  "})
        entries = registry.read_leaderboard(limit=10, sort="wins", min_rounds=0)
        assert len(entries) == 1
        # Latest casing wins for display_name; counters add up.
        assert entries[0]["display_name"] == "alice"
        assert entries[0]["princess_wins"] == 3
        assert entries[0]["rounds_played"] == 3
    finally:
        registry._conn.close()  # pylint: disable=protected-access


def test_bump_with_empty_order_is_noop(tmp_path):
    registry = RoomRegistry(db_path=str(tmp_path / "lb.db"))
    try:
        _bump(registry, [], {})
        assert registry.read_leaderboard(limit=10, sort="wins", min_rounds=0) == []
    finally:
        registry._conn.close()  # pylint: disable=protected-access


# --- bot exclusion + room hook --------------------------------------------


def _finish_two_player_game(room: Room, winner_pid: str, loser_pid: str) -> None:
    """Fabricate a finished Game on the room: winner first in finished_order."""
    players = [
        Player(pid=winner_pid, name=room.seat_by_pid(winner_pid).name),
        Player(pid=loser_pid, name=room.seat_by_pid(loser_pid).name),
    ]
    game = Game(players)
    game.finished_order = [winner_pid, loser_pid]
    game.game_over = True
    room.game = game
    room._scoreboard_counted_for_game = None  # pylint: disable=protected-access
    for seat in room.seats:
        room._ensure_scoreboard_entry(seat.pid)  # pylint: disable=protected-access


def test_room_bump_excludes_bots(tmp_db):
    room = Room(code="ABCD", host_pid="hA")
    room.seats.append(Seat(pid="hA", name="Alice", is_bot=False))
    room.seats.append(Seat(pid="bot1", name="Skill Issue", is_bot=True))
    _finish_two_player_game(room, winner_pid="hA", loser_pid="bot1")

    asyncio.run(room.broadcast_state())

    entries = tmp_db.read_leaderboard(limit=10, sort="wins", min_rounds=0)
    names = {r["display_name"] for r in entries}
    assert "Alice" in names
    assert "Skill Issue" not in names


def test_room_bump_is_idempotent_across_rebroadcasts(tmp_db):
    room = Room(code="EFGH", host_pid="hA")
    room.seats.append(Seat(pid="hA", name="Alice", is_bot=False))
    room.seats.append(Seat(pid="hB", name="Bob", is_bot=False))
    _finish_two_player_game(room, winner_pid="hA", loser_pid="hB")

    asyncio.run(room.broadcast_state())
    asyncio.run(room.broadcast_state())
    asyncio.run(room.broadcast_state())

    rows = {
        r["display_name"]: r for r in tmp_db.read_leaderboard(limit=10, sort="wins", min_rounds=0)
    }
    assert rows["Alice"]["princess_wins"] == 1
    assert rows["Alice"]["rounds_played"] == 1
    assert rows["Bob"]["last_places"] == 1
    assert rows["Bob"]["rounds_played"] == 1


def test_sqlite_error_does_not_raise(monkeypatch, tmp_db):
    """A write failure during bump must be logged, not raised."""

    def boom(_self, _upserts):
        raise sqlite3.Error("disk explode")

    monkeypatch.setattr(
        rooms_module.RoomRegistry,
        "_bump_global_leaderboard_sync",
        boom,
    )
    # Should not raise.
    asyncio.run(tmp_db.bump_global_leaderboard(["p1"], {"p1": "Alice"}))


# --- read endpoint ---------------------------------------------------------


@pytest.fixture
def lb_client(tmp_db):  # pylint: disable=unused-argument
    """TestClient with a writable leaderboard DB and a cleared cache."""
    server_module._LEADERBOARD_CACHE.clear()  # pylint: disable=protected-access
    return TestClient(app)


def test_endpoint_empty_returns_empty_list(lb_client):
    res = lb_client.get("/api/leaderboard")
    assert res.status_code == 200
    body = res.json()
    assert body["entries"] == []
    assert "generated_ts" in body


def test_endpoint_default_sort_by_wins(lb_client, tmp_db):
    _bump(tmp_db, ["pA"], {"pA": "Alice"})  # Alice +1 win
    _bump(tmp_db, ["pA"], {"pA": "Alice"})  # Alice +1 win
    _bump(tmp_db, ["pB"], {"pB": "Bob"})  # Bob +1 win
    server_module._LEADERBOARD_CACHE.clear()  # pylint: disable=protected-access

    res = lb_client.get("/api/leaderboard")
    assert res.status_code == 200
    entries = res.json()["entries"]
    assert [e["display_name"] for e in entries[:2]] == ["Alice", "Bob"]
    assert entries[0]["princess_wins"] == 2
    assert entries[0]["win_rate"] == 1.0


def test_endpoint_winrate_respects_min_rounds(lb_client, tmp_db):
    # Alice: 1 win, 1 round → win_rate 1.0 but only 1 round (below floor).
    _bump(tmp_db, ["pA"], {"pA": "Alice"})
    # Bob: 5 wins in 5 rounds — at the floor.
    for _ in range(5):
        _bump(tmp_db, ["pB"], {"pB": "Bob"})
    server_module._LEADERBOARD_CACHE.clear()  # pylint: disable=protected-access

    res = lb_client.get("/api/leaderboard?sort=winrate")
    assert res.status_code == 200
    names = [e["display_name"] for e in res.json()["entries"]]
    assert "Alice" not in names
    assert "Bob" in names


def test_endpoint_rounds_sort_orders_by_rounds(lb_client, tmp_db):
    for _ in range(3):
        _bump(tmp_db, ["pA"], {"pA": "Alice"})  # 3 rounds
    for _ in range(5):
        _bump(tmp_db, ["pB"], {"pB": "Bob"})  # 5 rounds
    server_module._LEADERBOARD_CACHE.clear()  # pylint: disable=protected-access

    res = lb_client.get("/api/leaderboard?sort=rounds")
    entries = res.json()["entries"]
    assert entries[0]["display_name"] == "Bob"
    assert entries[1]["display_name"] == "Alice"


def test_endpoint_rejects_bad_limit(lb_client):
    assert lb_client.get("/api/leaderboard?limit=0").status_code == 400
    assert lb_client.get("/api/leaderboard?limit=201").status_code == 400


def test_endpoint_rejects_bad_sort(lb_client):
    assert lb_client.get("/api/leaderboard?sort=nope").status_code == 400


def test_endpoint_caches_results(lb_client, tmp_db, monkeypatch):
    _bump(tmp_db, ["pA"], {"pA": "Alice"})
    server_module._LEADERBOARD_CACHE.clear()  # pylint: disable=protected-access

    calls = {"n": 0}
    real = rooms_module.RoomRegistry.read_leaderboard

    def counting(self, **kw):
        calls["n"] += 1
        return real(self, **kw)

    monkeypatch.setattr(rooms_module.RoomRegistry, "read_leaderboard", counting)

    lb_client.get("/api/leaderboard")
    lb_client.get("/api/leaderboard")
    lb_client.get("/api/leaderboard")
    assert calls["n"] == 1, "expected the second + third calls to hit the cache"


def test_endpoint_serves_page(lb_client):
    res = lb_client.get("/leaderboard")
    assert res.status_code == 200
    assert "Hall of Princesses" in res.text
    assert "leaderboard.js" in res.text


def test_desktop_footer_links_to_leaderboard(lb_client):
    res = lb_client.get("/")
    assert res.status_code == 200
    assert 'href="/leaderboard"' in res.text
    assert "Hall of Princesses" in res.text


def test_mobile_lobby_links_to_leaderboard(lb_client):
    res = lb_client.get("/m")
    assert res.status_code == 200
    assert 'href="/leaderboard"' in res.text
    assert "Hall of Princesses" in res.text
