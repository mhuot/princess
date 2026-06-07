#!/usr/bin/env python3
"""
Smoke tests for the FastAPI HTTP layer and WebSocket flow.

Copyright 2026 Mike Huot

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0
"""

from fastapi.testclient import TestClient

from princess.server import app
from princess import rooms as rooms_module


def _client() -> TestClient:
    # Reset the registry between tests. Mutate in place so server.REGISTRY
    # (a name-bound import) still points at the same object.
    rooms_module.REGISTRY._rooms.clear()  # pylint: disable=protected-access
    return TestClient(app)


def test_create_and_join_room():
    client = _client()
    res = client.post("/api/rooms", json={"name": "Ada"})
    assert res.status_code == 200
    code = res.json()["code"]
    assert len(code) == 4

    res2 = client.post(f"/api/rooms/{code}/join", json={"name": "Grace"})
    assert res2.status_code == 200
    assert res2.json()["code"] == code


def test_join_missing_room_404s():
    client = _client()
    res = client.post("/api/rooms/ZZZZ/join", json={"name": "Alan"})
    assert res.status_code == 404


def test_only_host_can_add_bot_and_start():
    client = _client()
    code = client.post("/api/rooms", json={"name": "Ada"}).json()["code"]
    join = client.post(f"/api/rooms/{code}/join", json={"name": "Grace"}).json()
    bad = client.post(f"/api/rooms/{code}/bot", json={"host_pid": join["pid"]})
    assert bad.status_code == 403
    bad_start = client.post(f"/api/rooms/{code}/start", json={"host_pid": join["pid"]})
    assert bad_start.status_code == 403


def test_full_websocket_round_trip():
    client = _client()
    create = client.post("/api/rooms", json={"name": "Ada"}).json()
    code, host_pid = create["code"], create["pid"]
    client.post(f"/api/rooms/{code}/bot", json={"host_pid": host_pid})
    with client.websocket_connect(f"/ws/{code}/{host_pid}") as ws:
        # Connection sends one direct lobby + one broadcast lobby.
        first = ws.receive_json()
        assert first["type"] == "lobby"
        echo = ws.receive_json()
        assert echo["type"] == "lobby"
        # POST /start triggers exactly one state broadcast (bots run loop returns
        # immediately because the game is in setup phase waiting on the human).
        client.post(f"/api/rooms/{code}/start", json={"host_pid": host_pid})
        msg = ws.receive_json()
        assert msg["type"] == "state"
        assert "you" in msg["view"]
        assert msg["view"]["phase"] == "setup"


# --- Config / abort / rematch / leave endpoint tests ------------------------


def _bootstrap_lobby(client: TestClient, host_name: str = "Ada") -> tuple[str, str]:
    create = client.post("/api/rooms", json={"name": host_name}).json()
    return create["code"], create["pid"]


def test_config_updates_seven_on_seven():
    client = _client()
    code, host_pid = _bootstrap_lobby(client)
    res = client.post(
        f"/api/rooms/{code}/config",
        json={"host_pid": host_pid, "config": {"seven_on_seven": False}},
    )
    assert res.status_code == 200
    assert res.json()["config"]["seven_on_seven"] is False


def test_config_rejected_for_non_host():
    client = _client()
    code, _host = _bootstrap_lobby(client)
    join = client.post(f"/api/rooms/{code}/join", json={"name": "Grace"}).json()
    res = client.post(
        f"/api/rooms/{code}/config",
        json={"host_pid": join["pid"], "config": {"seven_on_seven": False}},
    )
    assert res.status_code == 403


def test_config_rejected_after_game_starts():
    client = _client()
    code, host_pid = _bootstrap_lobby(client)
    client.post(f"/api/rooms/{code}/bot", json={"host_pid": host_pid})
    client.post(f"/api/rooms/{code}/start", json={"host_pid": host_pid})
    res = client.post(
        f"/api/rooms/{code}/config",
        json={"host_pid": host_pid, "config": {"seven_on_seven": False}},
    )
    assert res.status_code == 409


def test_config_ignores_unknown_keys():
    client = _client()
    code, host_pid = _bootstrap_lobby(client)
    res = client.post(
        f"/api/rooms/{code}/config",
        json={"host_pid": host_pid, "config": {"seven_on_seven": False, "fake_rule": True}},
    )
    assert res.status_code == 200
    cfg = res.json()["config"]
    assert cfg["seven_on_seven"] is False
    assert "fake_rule" not in cfg


def test_abort_returns_room_to_lobby():
    client = _client()
    code, host_pid = _bootstrap_lobby(client)
    client.post(f"/api/rooms/{code}/bot", json={"host_pid": host_pid})
    client.post(f"/api/rooms/{code}/start", json={"host_pid": host_pid})
    room = rooms_module.REGISTRY.get(code)
    assert room.game is not None
    res = client.post(f"/api/rooms/{code}/abort", json={"host_pid": host_pid})
    assert res.status_code == 200
    assert rooms_module.REGISTRY.get(code).game is None


def test_abort_rejected_for_non_host():
    client = _client()
    code, host_pid = _bootstrap_lobby(client)
    join = client.post(f"/api/rooms/{code}/join", json={"name": "Grace"}).json()
    client.post(f"/api/rooms/{code}/bot", json={"host_pid": host_pid})
    client.post(f"/api/rooms/{code}/start", json={"host_pid": host_pid})
    res = client.post(f"/api/rooms/{code}/abort", json={"host_pid": join["pid"]})
    assert res.status_code == 403


def test_abort_before_start_is_noop():
    client = _client()
    code, host_pid = _bootstrap_lobby(client)
    res = client.post(f"/api/rooms/{code}/abort", json={"host_pid": host_pid})
    assert res.status_code == 200


def test_rematch_requires_finished_game():
    client = _client()
    code, host_pid = _bootstrap_lobby(client)
    client.post(f"/api/rooms/{code}/bot", json={"host_pid": host_pid})
    client.post(f"/api/rooms/{code}/start", json={"host_pid": host_pid})
    # Game in progress, not over yet.
    res = client.post(f"/api/rooms/{code}/rematch", json={"host_pid": host_pid})
    assert res.status_code == 409


def test_rematch_starts_a_new_game_after_finish():
    client = _client()
    code, host_pid = _bootstrap_lobby(client)
    client.post(f"/api/rooms/{code}/bot", json={"host_pid": host_pid})
    client.post(f"/api/rooms/{code}/start", json={"host_pid": host_pid})
    room = rooms_module.REGISTRY.get(code)
    finished_game = room.game
    finished_game.game_over = True
    finished_game.finished_order = [room.seats[0].pid, room.seats[1].pid]
    res = client.post(f"/api/rooms/{code}/rematch", json={"host_pid": host_pid})
    assert res.status_code == 200
    new_game = rooms_module.REGISTRY.get(code).game
    assert new_game is not None
    assert new_game is not finished_game
    assert not new_game.game_over


def test_rematch_rejected_for_non_host():
    client = _client()
    code, host_pid = _bootstrap_lobby(client)
    join = client.post(f"/api/rooms/{code}/join", json={"name": "Grace"}).json()
    client.post(f"/api/rooms/{code}/start", json={"host_pid": host_pid})
    room = rooms_module.REGISTRY.get(code)
    room.game.game_over = True
    res = client.post(f"/api/rooms/{code}/rematch", json={"host_pid": join["pid"]})
    assert res.status_code == 403


def test_leave_removes_non_host_seat():
    client = _client()
    code, host_pid = _bootstrap_lobby(client)
    join = client.post(f"/api/rooms/{code}/join", json={"name": "Grace"}).json()
    room_before = rooms_module.REGISTRY.get(code)
    assert len(room_before.seats) == 2
    res = client.post(f"/api/rooms/{code}/leave", json={"pid": join["pid"]})
    assert res.status_code == 200
    room_after = rooms_module.REGISTRY.get(code)
    assert len(room_after.seats) == 1
    assert room_after.seats[0].pid == host_pid


def test_leave_rejects_host():
    client = _client()
    code, host_pid = _bootstrap_lobby(client)
    res = client.post(f"/api/rooms/{code}/leave", json={"pid": host_pid})
    assert res.status_code == 409


def test_leave_with_convert_to_bot_mid_game_keeps_seat():
    client = _client()
    code, host_pid = _bootstrap_lobby(client)
    join = client.post(f"/api/rooms/{code}/join", json={"name": "Grace"}).json()
    client.post(f"/api/rooms/{code}/start", json={"host_pid": host_pid})
    room = rooms_module.REGISTRY.get(code)
    # Force out of swap phase so the engine is in "playing".
    for player in room.game.players:
        if not player.ready:
            room.game.set_face_up(player.pid, [0, 1, 2])
    seat_count_before = len(room.seats)
    # Make sure it's NOT the converting seat's turn so run_bots is a no-op
    # immediately after conversion (otherwise the bot plays before we can read).
    target_pid = join["pid"]
    other_idx = next(i for i, p in enumerate(room.game.players) if p.pid != target_pid)
    room.game.current_idx = other_idx
    hand_before = list(room.game.player(target_pid).hand)
    res = client.post(
        f"/api/rooms/{code}/leave",
        json={"pid": target_pid, "convert_to_bot": True},
    )
    assert res.status_code == 200
    assert res.json()["converted"] is True
    assert len(room.seats) == seat_count_before  # seat preserved
    seat = room.seat_by_pid(target_pid)
    assert seat is not None and seat.is_bot
    # Hand is unchanged because it wasn't this seat's turn.
    assert room.game.player(target_pid).hand == hand_before


def test_leave_with_convert_to_bot_in_lobby_removes_seat():
    client = _client()
    code, _host_pid = _bootstrap_lobby(client)
    join = client.post(f"/api/rooms/{code}/join", json={"name": "Grace"}).json()
    room = rooms_module.REGISTRY.get(code)
    assert len(room.seats) == 2
    res = client.post(
        f"/api/rooms/{code}/leave",
        json={"pid": join["pid"], "convert_to_bot": True},
    )
    assert res.status_code == 200
    assert res.json()["converted"] is False
    assert len(room.seats) == 1


def test_leave_with_convert_to_bot_host_still_forbidden():
    client = _client()
    code, host_pid = _bootstrap_lobby(client)
    res = client.post(
        f"/api/rooms/{code}/leave",
        json={"pid": host_pid, "convert_to_bot": True},
    )
    assert res.status_code == 409


def test_end_round_success():
    client = _client()
    code, host_pid = _bootstrap_lobby(client)
    client.post(f"/api/rooms/{code}/bot", json={"host_pid": host_pid})
    client.post(f"/api/rooms/{code}/start", json={"host_pid": host_pid})
    room = rooms_module.REGISTRY.get(code)
    # Force out of swap phase so we have a "live" game with players holding cards.
    if room.game.phase == "setup":
        for player in room.game.players:
            if not player.ready:
                room.game.set_face_up(player.pid, [0, 1, 2])
    res = client.post(f"/api/rooms/{code}/end_round", json={"host_pid": host_pid})
    assert res.status_code == 200
    assert room.game.game_over
    assert len(room.game.finished_order) == len(room.seats)


def test_end_round_rejected_for_non_host():
    client = _client()
    code, host_pid = _bootstrap_lobby(client)
    join = client.post(f"/api/rooms/{code}/join", json={"name": "Grace"}).json()
    client.post(f"/api/rooms/{code}/start", json={"host_pid": host_pid})
    room = rooms_module.REGISTRY.get(code)
    if room.game.phase == "setup":
        for player in room.game.players:
            if not player.ready:
                room.game.set_face_up(player.pid, [0, 1, 2])
    res = client.post(f"/api/rooms/{code}/end_round", json={"host_pid": join["pid"]})
    assert res.status_code == 403


def test_end_round_rejected_when_already_over():
    client = _client()
    code, host_pid = _bootstrap_lobby(client)
    client.post(f"/api/rooms/{code}/bot", json={"host_pid": host_pid})
    client.post(f"/api/rooms/{code}/start", json={"host_pid": host_pid})
    room = rooms_module.REGISTRY.get(code)
    room.game.game_over = True
    res = client.post(f"/api/rooms/{code}/end_round", json={"host_pid": host_pid})
    assert res.status_code == 409


def test_leave_unknown_pid_is_idempotent():
    client = _client()
    code, _host = _bootstrap_lobby(client)
    res = client.post(f"/api/rooms/{code}/leave", json={"pid": "definitely-not-real"})
    assert res.status_code == 200
