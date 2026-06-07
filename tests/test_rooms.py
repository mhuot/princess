#!/usr/bin/env python3
"""
Tests for room-level behaviors that depend on the cap policy and orphan eviction.

Copyright 2026 Mike Huot

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0
"""

import asyncio

from princess import rooms as rooms_module
from princess.rooms import (
    BOT_CAP_BOTS_ONLY,
    BOT_CAP_WITH_HUMANS,
    Room,
    RoomRegistry,
    Seat,
)


def _bots_only_room() -> Room:
    room = Room(code="TEST", host_pid="bot-a")
    room.seats.append(Seat(pid="bot-a", name="Bot A", is_bot=True))
    room.seats.append(Seat(pid="bot-b", name="Bot B", is_bot=True))
    return room


def test_bot_action_cap_strict_when_connected_human_seated():
    class FakeSocket:  # pragma: no cover - shape only
        pass

    room = _bots_only_room()
    room.seats.append(Seat(pid="human", name="H", is_bot=False, socket=FakeSocket()))
    assert room._bot_action_cap() == BOT_CAP_WITH_HUMANS  # pylint: disable=protected-access


def test_bot_action_cap_lifted_when_human_disconnected():
    room = _bots_only_room()
    room.seats.append(Seat(pid="human", name="H", is_bot=False, socket=None))
    assert room._bot_action_cap() == BOT_CAP_BOTS_ONLY  # pylint: disable=protected-access


def test_bot_action_cap_lifted_when_all_bots():
    room = _bots_only_room()
    assert room._bot_action_cap() == BOT_CAP_BOTS_ONLY  # pylint: disable=protected-access


def test_bots_only_room_runs_past_human_cap(monkeypatch):
    """Construct a bot-only room and let run_bots play a real round to game-over.

    This indirectly proves the cap was lifted: a single Princess round between
    two bots routinely exceeds 30 plays. We patch the think delay to 0 so the
    test runs in milliseconds.
    """
    monkeypatch.setattr(rooms_module, "AI_THINK_SECONDS", 0)
    room = _bots_only_room()
    room.start_game()
    assert room.game.phase == "playing"
    asyncio.run(room.run_bots())
    assert room.game.game_over, "bot-only round should reach game_over"


def test_registry_evict_idle_drops_disconnected_rooms():
    registry = RoomRegistry()

    # Build two rooms by hand so we can manipulate timestamps.
    fresh = Room(code="FRESH", host_pid="h1")
    fresh.seats.append(Seat(pid="h1", name="Host", is_bot=False))
    fresh.last_activity_ts = 1000.0
    registry._rooms["FRESH"] = fresh  # pylint: disable=protected-access

    stale = Room(code="STALE", host_pid="h2")
    stale.seats.append(Seat(pid="h2", name="Host", is_bot=False))
    stale.last_activity_ts = 0.0  # very old
    registry._rooms["STALE"] = stale  # pylint: disable=protected-access

    # now=2000, timeout=300 → STALE is 2000s old → drop. FRESH is 1000s old → drop too.
    evicted = registry.evict_idle(timeout_seconds=300, now=2000.0)
    assert set(evicted) == {"FRESH", "STALE"}
    assert registry.get("FRESH") is None
    assert registry.get("STALE") is None


def test_registry_evict_idle_spares_active_rooms():
    registry = RoomRegistry()
    active = Room(code="ACTIVE", host_pid="h1")
    active.seats.append(Seat(pid="h1", name="Host", is_bot=False))
    active.last_activity_ts = 1990.0  # 10s ago
    registry._rooms["ACTIVE"] = active  # pylint: disable=protected-access

    evicted = registry.evict_idle(timeout_seconds=300, now=2000.0)
    assert evicted == []
    assert registry.get("ACTIVE") is active


def test_registry_evict_idle_spares_rooms_with_connected_sockets():
    """Even an idle room is kept if any seat has a live socket."""

    class FakeSocket:
        pass

    registry = RoomRegistry()
    room = Room(code="LIVE", host_pid="h1")
    seat = Seat(pid="h1", name="Host", is_bot=False, socket=FakeSocket())
    room.seats.append(seat)
    room.last_activity_ts = 0.0
    registry._rooms["LIVE"] = room  # pylint: disable=protected-access

    evicted = registry.evict_idle(timeout_seconds=300, now=2000.0)
    assert evicted == []
