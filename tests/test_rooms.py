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


def _zero_entry() -> dict:
    return {"princess_wins": 0, "last_places": 0, "rounds_played": 0}


def _seeded_room(pids: list[str]) -> Room:
    """Build a room whose seats are pre-registered in the scoreboard.

    Tests for the scoreboard bump path don't need a live `Game`; they synthesize
    a tiny stand-in object exposing only `game_over` and `finished_order`.
    """
    room = Room(code="SCORE", host_pid=pids[0])
    for pid in pids:
        room.seats.append(Seat(pid=pid, name=pid.upper(), is_bot=False))
        room._ensure_scoreboard_entry(pid)  # pylint: disable=protected-access
    return room


class _FakeGame:  # pylint: disable=too-few-public-methods
    def __init__(self, finished_order: list[str], game_over: bool = True) -> None:
        self.finished_order = list(finished_order)
        self.game_over = game_over


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
    """Construct a bot-only room and let run_bots play.

    The point of this test is the **cap was lifted past 30** — i.e., the bot
    loop is no longer capped at the strict human-waiting limit. We accept
    either a natural game-over (the typical outcome) OR the lifetime
    backstop firing (rare; happens when the unseeded AI RNG gets unlucky and
    the bots just keep picking up the pile from each other). Both prove the
    point. The bad outcome would be a deadlock at 30 — which a fast assertion
    on the deck would catch: an active round always burns through the deck
    well within 30 turns.

    We patch the think delay to 0 so the test runs in milliseconds.
    """
    monkeypatch.setattr(rooms_module, "AI_THINK_SECONDS", 0)
    room = _bots_only_room()
    room.start_game()
    assert room.game.phase == "playing"
    initial_deck = len(room.game.deck)
    asyncio.run(room.run_bots())
    # Cap-lifted proof: either game_over (typical) or deck was substantially
    # drained (>30 actions worth). Either rules out the 30-step strict cap.
    cap_lifted = room.game.game_over or (initial_deck - len(room.game.deck)) > 5
    assert cap_lifted, (
        "bot loop should have run past the 30-step human cap; "
        f"game_over={room.game.game_over}, deck_drained={initial_deck - len(room.game.deck)}"
    )


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


# --- Session scoreboard ------------------------------------------------------


def test_scoreboard_ensures_fresh_entry() -> None:
    room = Room(code="X", host_pid="p1")
    room._ensure_scoreboard_entry("p1")  # pylint: disable=protected-access
    assert room.scoreboard["p1"] == _zero_entry()


def test_scoreboard_ensure_is_idempotent_for_existing_pid() -> None:
    room = _seeded_room(["p1"])
    room.scoreboard["p1"]["princess_wins"] = 5
    room._ensure_scoreboard_entry("p1")  # pylint: disable=protected-access
    assert room.scoreboard["p1"]["princess_wins"] == 5


def test_scoreboard_drop_entry_removes_pid() -> None:
    room = _seeded_room(["p1", "p2"])
    room._drop_scoreboard_entry("p2")  # pylint: disable=protected-access
    assert "p2" not in room.scoreboard
    assert "p1" in room.scoreboard


def test_scoreboard_drop_missing_pid_is_noop() -> None:
    room = _seeded_room(["p1"])
    room._drop_scoreboard_entry("ghost")  # pylint: disable=protected-access
    assert "p1" in room.scoreboard


def test_scoreboard_bump_winner_and_last_place() -> None:
    room = _seeded_room(["p0", "p1", "p2"])
    room.game = _FakeGame(["p1", "p0", "p2"])
    room._bump_scoreboard_if_needed()  # pylint: disable=protected-access
    assert room.scoreboard["p1"]["princess_wins"] == 1
    assert room.scoreboard["p2"]["last_places"] == 1
    assert room.scoreboard["p0"]["last_places"] == 0
    for pid in ["p0", "p1", "p2"]:
        assert room.scoreboard[pid]["rounds_played"] == 1


def test_scoreboard_bump_is_idempotent_within_same_game() -> None:
    room = _seeded_room(["p0", "p1"])
    room.game = _FakeGame(["p0", "p1"])
    room._bump_scoreboard_if_needed()  # pylint: disable=protected-access
    room._bump_scoreboard_if_needed()  # pylint: disable=protected-access
    assert room.scoreboard["p0"]["princess_wins"] == 1
    assert room.scoreboard["p1"]["last_places"] == 1
    assert room.scoreboard["p0"]["rounds_played"] == 1
    assert room.scoreboard["p1"]["rounds_played"] == 1


def test_scoreboard_bump_skips_when_game_not_over() -> None:
    room = _seeded_room(["p0", "p1"])
    room.game = _FakeGame(["p0", "p1"], game_over=False)
    room._bump_scoreboard_if_needed()  # pylint: disable=protected-access
    assert room.scoreboard["p0"] == _zero_entry()


def test_scoreboard_two_player_bumps_both_ranks() -> None:
    room = _seeded_room(["p0", "p1"])
    room.game = _FakeGame(["p0", "p1"])
    room._bump_scoreboard_if_needed()  # pylint: disable=protected-access
    assert room.scoreboard["p0"]["princess_wins"] == 1
    assert room.scoreboard["p1"]["last_places"] == 1


def test_scoreboard_rematch_preserves_counts_and_recounts_new_game() -> None:
    room = _seeded_room(["p0", "p1"])
    room.game = _FakeGame(["p0", "p1"])
    room._bump_scoreboard_if_needed()  # pylint: disable=protected-access
    # Simulate `start_game` clearing the counted marker for a new round.
    room._scoreboard_counted_for_game = None  # pylint: disable=protected-access
    room.game = _FakeGame(["p1", "p0"])
    room._bump_scoreboard_if_needed()  # pylint: disable=protected-access
    assert room.scoreboard["p0"]["princess_wins"] == 1
    assert room.scoreboard["p1"]["princess_wins"] == 1
    assert room.scoreboard["p0"]["rounds_played"] == 2
    assert room.scoreboard["p1"]["rounds_played"] == 2


def test_scoreboard_reset_zeros_existing_entries() -> None:
    room = _seeded_room(["p0", "p1"])
    room.scoreboard["p0"]["princess_wins"] = 3
    room.scoreboard["p1"]["last_places"] = 2
    room.reset_scoreboard()
    assert room.scoreboard["p0"] == _zero_entry()
    assert room.scoreboard["p1"] == _zero_entry()
    assert set(room.scoreboard.keys()) == {"p0", "p1"}


def test_scoreboard_public_lobby_includes_scoreboard() -> None:
    room = _seeded_room(["p0", "p1"])
    room.scoreboard["p0"]["princess_wins"] = 4
    payload = room.public_lobby()
    assert payload["scoreboard"]["p0"]["princess_wins"] == 4
    # The dict is a copy — mutating the broadcast must not poke back.
    payload["scoreboard"]["p0"]["princess_wins"] = 99
    assert room.scoreboard["p0"]["princess_wins"] == 4


def test_scoreboard_skips_unknown_pid_defensively() -> None:
    room = _seeded_room(["p0"])
    room.game = _FakeGame(["p0", "ghost"])
    # The defensive guard must skip "ghost" without raising even though it has
    # no scoreboard entry; the seated winner still gets credit.
    room._bump_scoreboard_if_needed()  # pylint: disable=protected-access
    assert room.scoreboard["p0"]["princess_wins"] == 1
    assert "ghost" not in room.scoreboard


def test_registry_create_seeds_host_scoreboard_entry() -> None:
    registry = RoomRegistry()
    room = asyncio.run(registry.create(host_pid="host", host_name="Host"))
    assert room.scoreboard["host"] == _zero_entry()
