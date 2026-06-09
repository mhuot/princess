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


def test_mobile_routes_serve_mobile_html():
    client = _client()
    res = client.get("/m")
    assert res.status_code == 200
    assert "mobile" in res.text.lower()
    res2 = client.get("/m/AB12")
    assert res2.status_code == 200
    assert res2.text == res.text  # same file


# --- UA-based mobile redirect tests ----------------------------------------


_DESKTOP_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
)
_IPHONE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)
_IPAD_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
)


def test_index_serves_desktop_for_desktop_ua():
    client = _client()
    res = client.get("/", headers={"user-agent": _DESKTOP_UA})
    assert res.status_code == 200
    assert "Princess Card Game" in res.text


def test_index_redirects_mobile_ua_to_m():
    client = _client()
    res = client.get("/", headers={"user-agent": _IPHONE_UA}, follow_redirects=False)
    assert res.status_code == 302
    assert res.headers["location"] == "/m"


def test_room_page_redirects_mobile_ua():
    client = _client()
    res = client.get(
        "/room/AB12",
        headers={"user-agent": _IPHONE_UA},
        follow_redirects=False,
    )
    assert res.status_code == 302
    assert res.headers["location"] == "/m/AB12"


def test_desktop_query_override_blocks_redirect():
    client = _client()
    res = client.get(
        "/?desktop=1",
        headers={"user-agent": _IPHONE_UA},
        follow_redirects=False,
    )
    assert res.status_code == 200
    assert "Princess Card Game" in res.text


def test_cookie_override_blocks_redirect():
    client = _client()
    client.cookies.set("princess_prefer_desktop", "1")
    res = client.get("/", headers={"user-agent": _IPHONE_UA}, follow_redirects=False)
    assert res.status_code == 200
    assert "Princess Card Game" in res.text


def test_m_serves_mobile_for_desktop_ua():
    client = _client()
    res = client.get("/m", headers={"user-agent": _DESKTOP_UA})
    assert res.status_code == 200
    assert "Princess — mobile" in res.text


def test_ipad_serves_desktop():
    # iPad (since iPadOS 13) reports a desktop-like UA with no "Mobi".
    client = _client()
    res = client.get("/", headers={"user-agent": _IPAD_UA}, follow_redirects=False)
    assert res.status_code == 200
    assert "Princess Card Game" in res.text


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


def test_config_updates_reverse_rank():
    client = _client()
    code, host_pid = _bootstrap_lobby(client)
    res = client.post(
        f"/api/rooms/{code}/config",
        json={"host_pid": host_pid, "config": {"reverse_rank": 13}},
    )
    assert res.status_code == 200
    cfg = res.json()["config"]
    assert cfg["reverse_rank"] == 13
    assert "same_on_reverse" not in cfg
    room = rooms_module.REGISTRY.get(code)
    assert room.config.reverse_rank == 13
    assert not hasattr(room.config, "same_on_reverse")


def test_config_rejected_for_non_host():
    client = _client()
    code, _host = _bootstrap_lobby(client)
    join = client.post(f"/api/rooms/{code}/join", json={"name": "Grace"}).json()
    res = client.post(
        f"/api/rooms/{code}/config",
        json={"host_pid": join["pid"], "config": {"reverse_rank": 7}},
    )
    assert res.status_code == 403


def test_config_rejected_after_game_starts():
    client = _client()
    code, host_pid = _bootstrap_lobby(client)
    client.post(f"/api/rooms/{code}/bot", json={"host_pid": host_pid})
    client.post(f"/api/rooms/{code}/start", json={"host_pid": host_pid})
    res = client.post(
        f"/api/rooms/{code}/config",
        json={"host_pid": host_pid, "config": {"reverse_rank": 7}},
    )
    assert res.status_code == 409


def test_config_ignores_unknown_keys():
    client = _client()
    code, host_pid = _bootstrap_lobby(client)
    res = client.post(
        f"/api/rooms/{code}/config",
        json={
            "host_pid": host_pid,
            "config": {
                "reverse_rank": 9,
                "same_on_reverse": True,  # legacy — silently dropped
                "seven_on_seven": False,  # legacy — silently dropped
                "fake_rule": True,
            },
        },
    )
    assert res.status_code == 200
    cfg = res.json()["config"]
    assert cfg["reverse_rank"] == 9
    assert "same_on_reverse" not in cfg
    assert "seven_on_seven" not in cfg
    assert "fake_rule" not in cfg


# --- Remove-bot / rename endpoint tests -------------------------------------


def _bot_pid_of(room, name=None):
    for s in room.seats:
        if s.is_bot and (name is None or s.name == name):
            return s.pid
    return None


def test_remove_bot_success():
    client = _client()
    code, host_pid = _bootstrap_lobby(client)
    client.post(f"/api/rooms/{code}/bot", json={"host_pid": host_pid})
    client.post(f"/api/rooms/{code}/bot", json={"host_pid": host_pid})
    room = rooms_module.REGISTRY.get(code)
    assert len(room.seats) == 3
    target = _bot_pid_of(room)
    res = client.post(
        f"/api/rooms/{code}/remove_bot",
        json={"host_pid": host_pid, "bot_pid": target},
    )
    assert res.status_code == 200
    room = rooms_module.REGISTRY.get(code)
    assert len(room.seats) == 2
    assert all(s.pid != target for s in room.seats)


def test_remove_bot_rejects_non_host():
    client = _client()
    code, host_pid = _bootstrap_lobby(client)
    client.post(f"/api/rooms/{code}/bot", json={"host_pid": host_pid})
    join = client.post(f"/api/rooms/{code}/join", json={"name": "Grace"}).json()
    room = rooms_module.REGISTRY.get(code)
    target = _bot_pid_of(room)
    res = client.post(
        f"/api/rooms/{code}/remove_bot",
        json={"host_pid": join["pid"], "bot_pid": target},
    )
    assert res.status_code == 403


def test_remove_bot_rejects_after_start():
    client = _client()
    code, host_pid = _bootstrap_lobby(client)
    client.post(f"/api/rooms/{code}/bot", json={"host_pid": host_pid})
    client.post(f"/api/rooms/{code}/start", json={"host_pid": host_pid})
    room = rooms_module.REGISTRY.get(code)
    target = _bot_pid_of(room)
    res = client.post(
        f"/api/rooms/{code}/remove_bot",
        json={"host_pid": host_pid, "bot_pid": target},
    )
    assert res.status_code == 409


def test_remove_bot_rejects_human_seat():
    client = _client()
    code, host_pid = _bootstrap_lobby(client)
    join = client.post(f"/api/rooms/{code}/join", json={"name": "Grace"}).json()
    res = client.post(
        f"/api/rooms/{code}/remove_bot",
        json={"host_pid": host_pid, "bot_pid": join["pid"]},
    )
    assert res.status_code == 409


def test_remove_bot_unknown_bot_pid():
    client = _client()
    code, host_pid = _bootstrap_lobby(client)
    res = client.post(
        f"/api/rooms/{code}/remove_bot",
        json={"host_pid": host_pid, "bot_pid": "definitely-not-real"},
    )
    assert res.status_code == 404


def test_rename_in_lobby_updates_seat():
    client = _client()
    code, host_pid = _bootstrap_lobby(client, host_name="Ada")
    res = client.post(
        f"/api/rooms/{code}/rename",
        json={"pid": host_pid, "new_name": "Alan"},
    )
    assert res.status_code == 200
    assert res.json()["name"] == "Alan"
    room = rooms_module.REGISTRY.get(code)
    seat = room.seat_by_pid(host_pid)
    assert seat.name == "Alan"


def test_rename_mid_game_updates_seat_and_player():
    client = _client()
    code, host_pid = _bootstrap_lobby(client, host_name="Ada")
    client.post(f"/api/rooms/{code}/bot", json={"host_pid": host_pid})
    client.post(f"/api/rooms/{code}/start", json={"host_pid": host_pid})
    res = client.post(
        f"/api/rooms/{code}/rename",
        json={"pid": host_pid, "new_name": "Alan"},
    )
    assert res.status_code == 200
    room = rooms_module.REGISTRY.get(code)
    assert room.seat_by_pid(host_pid).name == "Alan"
    assert room.game.player(host_pid).name == "Alan"


def test_rename_unknown_pid_returns_404():
    client = _client()
    code, _host = _bootstrap_lobby(client)
    res = client.post(
        f"/api/rooms/{code}/rename",
        json={"pid": "ghost", "new_name": "Whoever"},
    )
    assert res.status_code == 404


def test_rename_empty_name_returns_422():
    client = _client()
    code, host_pid = _bootstrap_lobby(client)
    res = client.post(
        f"/api/rooms/{code}/rename",
        json={"pid": host_pid, "new_name": ""},
    )
    assert res.status_code == 422


def test_rename_overlong_name_returns_422():
    client = _client()
    code, host_pid = _bootstrap_lobby(client)
    res = client.post(
        f"/api/rooms/{code}/rename",
        json={"pid": host_pid, "new_name": "X" * 21},
    )
    assert res.status_code == 422


# --- Unique-name dedupe tests ----------------------------------------------


def test_join_rejects_duplicate_name():
    client = _client()
    code, _host_pid = _bootstrap_lobby(client, host_name="Ada")
    res = client.post(f"/api/rooms/{code}/join", json={"name": "Ada"})
    assert res.status_code == 409
    assert "'Ada'" in res.json()["detail"]


def test_join_rejects_case_insensitive_duplicate():
    client = _client()
    code, _host_pid = _bootstrap_lobby(client, host_name="Mike")
    res = client.post(f"/api/rooms/{code}/join", json={"name": "mike"})
    assert res.status_code == 409


def test_join_rejects_whitespace_padded_duplicate():
    client = _client()
    code, _host_pid = _bootstrap_lobby(client, host_name="Mike")
    res = client.post(f"/api/rooms/{code}/join", json={"name": "  Mike  "})
    assert res.status_code == 409


def test_join_rejects_name_matching_a_bot():
    client = _client()
    code, host_pid = _bootstrap_lobby(client)
    bot_res = client.post(f"/api/rooms/{code}/bot", json={"host_pid": host_pid})
    bot_name = bot_res.json()["name"]
    res = client.post(f"/api/rooms/{code}/join", json={"name": bot_name})
    assert res.status_code == 409


def test_rename_rejects_duplicate_name():
    client = _client()
    code, _host_pid = _bootstrap_lobby(client, host_name="Mike")
    join = client.post(f"/api/rooms/{code}/join", json={"name": "Pat"}).json()
    res = client.post(
        f"/api/rooms/{code}/rename",
        json={"pid": join["pid"], "new_name": "Mike"},
    )
    assert res.status_code == 409
    assert "'Mike'" in res.json()["detail"]


def test_rename_to_own_name_is_noop():
    client = _client()
    code, host_pid = _bootstrap_lobby(client, host_name="Mike")
    room = rooms_module.REGISTRY.get(code)
    # Snapshot before
    before_name = room.seats[0].name
    res = client.post(
        f"/api/rooms/{code}/rename",
        json={"pid": host_pid, "new_name": "  MIKE  "},
    )
    assert res.status_code == 200
    # No state change — original casing preserved.
    assert room.seats[0].name == before_name


def test_create_room_trims_host_name():
    client = _client()
    res = client.post("/api/rooms", json={"name": "  Mike  "})
    assert res.status_code == 200
    code = res.json()["code"]
    room = rooms_module.REGISTRY.get(code)
    assert room.seats[0].name == "Mike"


def test_bot_name_avoids_human_name():
    client = _client()
    code, host_pid = _bootstrap_lobby(client, host_name="Galaxy Brain")
    res = client.post(f"/api/rooms/{code}/bot", json={"host_pid": host_pid})
    assert res.status_code == 200
    assert res.json()["name"] != "Galaxy Brain"


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


def test_healthz_returns_ok():
    client = _client()
    res = client.get("/healthz")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert isinstance(body["uptime_seconds"], int)
    assert body["uptime_seconds"] >= 0
    assert isinstance(body["rooms"], int)
    assert body["rooms"] >= 0
    assert isinstance(body["log_buffer_size"], int)
    assert body["log_buffer_size"] >= 0


def test_healthz_reports_room_count():
    client = _client()
    client.post("/api/rooms", json={"name": "Ada"})
    client.post("/api/rooms", json={"name": "Grace"})
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.json()["rooms"] == 2


def test_healthz_unaffected_by_mobile_ua():
    client = _client()
    res = client.get(
        "/healthz",
        headers={"user-agent": _IPHONE_UA},
        follow_redirects=False,
    )
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
