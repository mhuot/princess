#!/usr/bin/env python3
"""
Tests for SQLite-backed room persistence.

Covers engine-level serialization round-trips, ``Room`` round-trip, the
``RoomRegistry`` persist/forget/restore path, eviction cleanup, lifespan
startup, and that a failed write does not raise out of a handler.

Copyright 2026 Mike Huot

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0
"""

from __future__ import annotations

import ast
import asyncio
import json
import logging
import sqlite3
from pathlib import Path

from princess.cards import Card, make_deck
from princess.game import Game, GameConfig, Player, Source
from princess.rooms import REGISTRY, Room, RoomRegistry, Seat
from princess.server import app, lifespan

# --- engine round-trips ------------------------------------------------------


def test_card_round_trip() -> None:
    for c in make_deck():
        assert Card.from_dict(c.to_dict()) == c


def test_player_round_trip() -> None:
    player = Player(
        pid="p1",
        name="Alice",
        hand=[Card(7, "S"), Card(2, "H")],
        face_up=[Card(13, "C")],
        face_down=[Card(5, "D")],
        choose=[Card(11, "S"), Card(4, "C")],
        finished=False,
        ready=True,
    )
    restored = Player.from_dict(player.to_dict())
    assert restored == player


def test_game_from_dict_skips_setup() -> None:
    players = [Player(pid=f"p{i}", name=f"P{i}") for i in range(3)]
    game = Game(players, seed=42)
    # Advance state a bit so deck/hands/pile are non-trivial.
    current = game.current_player
    src = game.active_source(current)
    assert src is Source.HAND
    legal_idx = next(
        (i for i, c in enumerate(current.hand) if game.is_legal_rank(c.rank)),
        None,
    )
    if legal_idx is not None:
        game.play(current.pid, Source.HAND, [legal_idx])
    snapshot = game.to_dict()
    restored = Game.from_dict(snapshot)
    assert restored.to_dict() == snapshot
    # Deck length is preserved exactly — not re-dealt.
    assert len(restored.deck) == len(game.deck)
    assert [c.label for c in restored.pile] == [c.label for c in game.pile]


def test_engine_modules_have_no_sqlite_import() -> None:
    """Spec invariant — engine stays pure of storage concerns."""
    for module_name in ("princess/cards.py", "princess/game.py"):
        path = Path(__file__).resolve().parent.parent / module_name
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name != "sqlite3", f"{module_name} imports sqlite3"
            elif isinstance(node, ast.ImportFrom):
                assert node.module != "sqlite3", f"{module_name} imports sqlite3"


# --- Room round-trips --------------------------------------------------------


def _lobby_room() -> Room:
    room = Room(code="ABCD", host_pid="host")
    room.seats.append(Seat(pid="host", name="Host", is_bot=False))
    room.seats.append(Seat(pid="guest", name="Guest", is_bot=False))
    room.seats.append(Seat(pid="bot1", name="Bot 1", is_bot=True))
    for pid in ("host", "guest", "bot1"):
        room._ensure_scoreboard_entry(pid)  # pylint: disable=protected-access
    room.scoreboard["host"]["princess_wins"] = 2
    return room


def test_room_to_from_dict_lobby() -> None:
    room = _lobby_room()
    restored = Room.from_dict(room.to_dict())
    assert restored.code == room.code
    assert restored.host_pid == room.host_pid
    assert [(s.pid, s.name, s.is_bot, s.socket) for s in restored.seats] == [
        (s.pid, s.name, s.is_bot, None) for s in room.seats
    ]
    assert restored.config.to_dict() == room.config.to_dict()
    assert restored.game is None
    assert restored.scoreboard == room.scoreboard


def test_room_to_from_dict_in_progress() -> None:
    room = _lobby_room()
    # Replace bot seat with a third human so 3 players play.
    room.seats[-1] = Seat(pid="bot1", name="Bot 1", is_bot=False)
    room.start_game()
    # Force out of setup by simulating face-up picks.
    for seat in room.seats:
        room.game.set_face_up(seat.pid, [0, 1, 2])
    assert room.game.phase == "playing"
    snapshot = room.to_dict()
    restored = Room.from_dict(snapshot)
    assert restored.game is not None
    assert restored.game.to_dict() == room.game.to_dict()


# --- registry persist/restore -----------------------------------------------


def test_registry_persist_and_restore_lobby(tmp_db: RoomRegistry) -> None:
    room = asyncio.run(tmp_db.create(host_pid="host", host_name="Host"))
    code = room.code
    # Fresh registry against the same DB sees the room.
    fresh = RoomRegistry(db_path=tmp_db._db_path)  # pylint: disable=protected-access
    restored_count = fresh.restore_all()
    assert restored_count == 1
    assert fresh.get(code) is not None
    assert fresh.get(code).host_pid == "host"


def test_registry_persist_and_restore_mid_round(tmp_db: RoomRegistry) -> None:
    room = asyncio.run(tmp_db.create(host_pid="host", host_name="Host"))
    room.seats.append(Seat(pid="p2", name="P2", is_bot=False))
    room._ensure_scoreboard_entry("p2")  # pylint: disable=protected-access
    room.start_game()
    for seat in room.seats:
        room.game.set_face_up(seat.pid, [0, 1, 2])
    asyncio.run(tmp_db.persist(room))

    fresh = RoomRegistry(db_path=tmp_db._db_path)  # pylint: disable=protected-access
    fresh.restore_all()
    restored = fresh.get(room.code)
    assert restored is not None
    assert restored.game is not None
    assert restored.game.to_dict() == room.game.to_dict()


def test_registry_persist_after_join(tmp_db: RoomRegistry) -> None:
    room = asyncio.run(tmp_db.create(host_pid="h", host_name="Host"))
    room.seats.append(Seat(pid="g", name="Guest", is_bot=False))
    asyncio.run(tmp_db.persist(room))
    fresh = RoomRegistry(db_path=tmp_db._db_path)  # pylint: disable=protected-access
    fresh.restore_all()
    restored = fresh.get(room.code)
    assert restored is not None
    assert [s.pid for s in restored.seats] == ["h", "g"]


def test_corrupt_row_is_skipped(tmp_db: RoomRegistry, caplog) -> None:
    # Insert a valid room.
    good = asyncio.run(tmp_db.create(host_pid="h", host_name="Host"))
    # And a corrupt row alongside it.
    conn = tmp_db._conn  # pylint: disable=protected-access
    conn.execute(
        "INSERT OR REPLACE INTO rooms (code, payload, updated_ts) VALUES (?, ?, ?)",
        ("BADD", "{not valid json", 0.0),
    )
    fresh = RoomRegistry(db_path=tmp_db._db_path)  # pylint: disable=protected-access
    with caplog.at_level(logging.ERROR, logger="princess.persistence"):
        count = fresh.restore_all()
    assert count == 1
    assert fresh.get(good.code) is not None
    assert fresh.get("BADD") is None
    assert any("BADD" in rec.getMessage() for rec in caplog.records)


def test_evict_idle_deletes_row(tmp_db: RoomRegistry) -> None:
    room = asyncio.run(tmp_db.create(host_pid="h", host_name="Host"))
    # Make it look idle.
    room.last_activity_ts = 0.0
    evicted = tmp_db.evict_idle(timeout_seconds=10, now=1_000_000.0)
    assert room.code in evicted
    fresh = RoomRegistry(db_path=tmp_db._db_path)  # pylint: disable=protected-access
    assert fresh.restore_all() == 0


def test_remove_deletes_row(tmp_db: RoomRegistry) -> None:
    room = asyncio.run(tmp_db.create(host_pid="h", host_name="Host"))
    asyncio.run(tmp_db.remove(room.code))
    fresh = RoomRegistry(db_path=tmp_db._db_path)  # pylint: disable=protected-access
    assert fresh.restore_all() == 0


def test_unknown_schema_version_is_skipped(tmp_db: RoomRegistry) -> None:
    bad_payload = json.dumps(
        {
            "schema_version": 999,
            "code": "XXXX",
            "host_pid": "h",
            "seats": [],
            "config": GameConfig().to_dict(),
            "game": None,
            "scoreboard": {},
            "scoreboard_counted_for_game": None,
            "wall_last_activity_ts": 0.0,
        }
    )
    tmp_db._conn.execute(  # pylint: disable=protected-access
        "INSERT OR REPLACE INTO rooms (code, payload, updated_ts) VALUES (?, ?, ?)",
        ("XXXX", bad_payload, 0.0),
    )
    fresh = RoomRegistry(db_path=tmp_db._db_path)  # pylint: disable=protected-access
    assert fresh.restore_all() == 0


def test_persist_error_is_logged_not_raised(tmp_db: RoomRegistry, caplog) -> None:
    """A SQLite write that raises must not crash the handler."""
    room = asyncio.run(tmp_db.create(host_pid="h", host_name="Host"))

    def boom(*_args, **_kwargs):
        raise sqlite3.OperationalError("disk is on fire")

    # Replace the sync helper for the duration of the test.
    original = tmp_db._persist_sync  # pylint: disable=protected-access
    tmp_db._persist_sync = boom  # type: ignore[assignment]  # pylint: disable=protected-access
    try:
        with caplog.at_level(logging.ERROR, logger="princess.persistence"):
            # Should not raise.
            asyncio.run(tmp_db.persist(room))
    finally:
        tmp_db._persist_sync = original  # type: ignore[assignment]  # pylint: disable=protected-access
    assert any(room.code in rec.getMessage() for rec in caplog.records)


# --- env / lifespan startup --------------------------------------------------


def test_default_db_path(tmp_path, monkeypatch) -> None:
    """With ``PRINCESS_DB_PATH`` unset the lifespan creates ``./princess.db``."""
    monkeypatch.delenv("PRINCESS_DB_PATH", raising=False)
    monkeypatch.chdir(tmp_path)
    # Save and reset the registry connection.
    prev_conn = REGISTRY._conn  # pylint: disable=protected-access
    REGISTRY._conn = None  # pylint: disable=protected-access
    REGISTRY._db_path = None  # pylint: disable=protected-access
    try:

        async def _run() -> None:
            async with lifespan(app):
                pass

        asyncio.run(_run())
        assert (tmp_path / "princess.db").exists()
    finally:
        if REGISTRY._conn is not None:  # pylint: disable=protected-access
            REGISTRY._conn.close()  # pylint: disable=protected-access
        REGISTRY._conn = prev_conn  # pylint: disable=protected-access


def test_env_db_path_override(tmp_path, monkeypatch) -> None:
    custom = tmp_path / "elsewhere" / "rooms.db"
    custom.parent.mkdir()
    monkeypatch.setenv("PRINCESS_DB_PATH", str(custom))
    monkeypatch.chdir(tmp_path)
    prev_conn = REGISTRY._conn  # pylint: disable=protected-access
    REGISTRY._conn = None  # pylint: disable=protected-access
    REGISTRY._db_path = None  # pylint: disable=protected-access
    try:

        async def _run() -> None:
            async with lifespan(app):
                pass

        asyncio.run(_run())
        assert custom.exists()
        assert not (tmp_path / "princess.db").exists()
    finally:
        if REGISTRY._conn is not None:  # pylint: disable=protected-access
            REGISTRY._conn.close()  # pylint: disable=protected-access
        REGISTRY._conn = prev_conn  # pylint: disable=protected-access


# --- guard against silent drift ---------------------------------------------


def test_round_trip_through_to_dict_is_stable() -> None:
    """``to_dict ∘ from_dict ∘ to_dict`` is invariant on every field
    except the wall-clock activity stamp, which moves with the clock."""
    room = _lobby_room()
    once = room.to_dict()
    twice = Room.from_dict(once).to_dict()
    for key, value in once.items():
        if key == "wall_last_activity_ts":
            continue
        assert value == twice[key], f"field drifted: {key}"
