#!/usr/bin/env python3
"""
In-memory room registry and lifecycle for Princess Card Game.

A Room owns:
- a list of human and bot Players
- a Game (created when the host clicks Start)
- the set of connected WebSockets
- a lock to serialize state mutations

Copyright 2026 Mike Huot

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0
"""

from __future__ import annotations

import asyncio
import random
import secrets
import string
import time
from dataclasses import dataclass, field

from fastapi import WebSocket

from .ai import decide
from .game import Game, GameConfig, Player, Source
from .logging_config import room_logger

ROOM_CODE_CHARS = string.ascii_uppercase + string.digits
ROOM_CODE_LEN = 4
MAX_PLAYERS = 4
MIN_PLAYERS = 2
AI_THINK_SECONDS = 0.6
BOT_CAP_WITH_HUMANS = 30
BOT_CAP_BOTS_ONLY = 1000


def _new_code() -> str:
    return "".join(secrets.choice(ROOM_CODE_CHARS) for _ in range(ROOM_CODE_LEN))


@dataclass
class Seat:
    pid: str
    name: str
    is_bot: bool = False
    socket: WebSocket | None = None


@dataclass
class Room:
    code: str
    host_pid: str
    seats: list[Seat] = field(default_factory=list)
    game: Game | None = None
    config: GameConfig = field(default_factory=GameConfig)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    last_activity_ts: float = field(default_factory=time.monotonic)

    def touch(self) -> None:
        """Mark the room as recently active so the idle sweep spares it."""
        self.last_activity_ts = time.monotonic()

    def seat_by_pid(self, pid: str) -> Seat | None:
        for seat in self.seats:
            if seat.pid == pid:
                return seat
        return None

    def public_lobby(self) -> dict:
        return {
            "code": self.code,
            "host_pid": self.host_pid,
            "seats": [
                {
                    "pid": s.pid,
                    "name": s.name,
                    "is_bot": s.is_bot,
                    "connected": s.socket is not None,
                }
                for s in self.seats
            ],
            "started": self.game is not None,
            "config": self.config.to_dict(),
        }

    async def broadcast_lobby(self) -> None:
        msg = {"type": "lobby", "room": self.public_lobby()}
        await self._broadcast(msg)

    async def broadcast_state(self) -> None:
        if self.game is None:
            await self.broadcast_lobby()
            return
        bot_pids = {s.pid for s in self.seats if s.is_bot}
        for seat in self.seats:
            if seat.is_bot or seat.socket is None:
                continue
            view = self.game.view_for(seat.pid, bot_pids=bot_pids)
            await self._send(seat.socket, {"type": "state", "view": view})

    async def _broadcast(self, msg: dict) -> None:
        for seat in self.seats:
            if seat.socket is None:
                continue
            await self._send(seat.socket, msg)

    async def _send(self, socket: WebSocket, msg: dict) -> None:
        try:
            await socket.send_json(msg)
        except (RuntimeError, ConnectionError):
            pass

    def start_game(self) -> None:
        self.touch()
        rlog = room_logger(self.code)
        players = [Player(pid=s.pid, name=s.name) for s in self.seats]
        self.game = Game(players, swap_phase=True, config=self.config)
        rlog.info(
            "game initialized phase=%s seats=%s config=%s",
            self.game.phase,
            [(s.name, "bot" if s.is_bot else "human") for s in self.seats],
            self.config.to_dict(),
        )
        # Bots auto-pick their three highest-ranked cards for face-up.
        for seat in self.seats:
            if seat.is_bot:
                self._auto_pick_bot_face_up(seat.pid)

    def _auto_pick_bot_face_up(self, pid: str) -> None:
        """Pick the top-3 highest-rank cards from this seat's choose pile.
        No-op if there is no game, the phase isn't setup, or the player is
        already ready."""
        if self.game is None or self.game.phase != "setup":
            return
        player = self.game.player(pid)
        if player.ready or not player.choose:
            return
        ranked = sorted(
            range(len(player.choose)),
            key=lambda i, p=player: p.choose[i].rank,
            reverse=True,
        )
        result = self.game.set_face_up(pid, ranked[:3])
        room_logger(self.code).debug(
            "bot auto-pick face_up pid=%s indices=%s ok=%s",
            pid,
            ranked[:3],
            result.ok,
        )

    def reset_for_rematch(self) -> None:
        self.game = None

    def _humans_seated(self) -> bool:
        """A human is 'seated' for cap purposes if their seat is flagged human
        AND they have a live WebSocket. A disconnected human can't be unblocked
        by us, so the strict cap doesn't help them — lift it and let bots play."""
        return any(not s.is_bot and s.socket is not None for s in self.seats)

    def _bot_action_cap(self) -> int:
        """Strict cap while a connected human waits; lifted otherwise."""
        return BOT_CAP_WITH_HUMANS if self._humans_seated() else BOT_CAP_BOTS_ONLY

    async def run_bots(self) -> None:
        """If it's a bot's turn, take its action(s) until a human's turn."""
        if self.game is None or self.game.phase != "playing":
            return
        rng = random.Random()
        rlog = room_logger(self.code)
        # Re-evaluate the cap each iteration so a mid-loop disconnect lifts it.
        # The lifetime backstop is BOT_CAP_BOTS_ONLY in either case.
        for step in range(BOT_CAP_BOTS_ONLY):
            if step >= self._bot_action_cap():
                # We've crossed the strict cap and a connected human is still
                # waiting — bail so we don't block them indefinitely.
                if self._humans_seated():
                    rlog.error(
                        "bot loop hit %d-step safety cap; halting to keep humans unblocked",
                        BOT_CAP_WITH_HUMANS,
                    )
                    return
            if self.game.game_over:
                return
            current = self.game.current_player
            seat = self.seat_by_pid(current.pid)
            if seat is None or not seat.is_bot:
                return
            top = self.game.pile[-1].label if self.game.pile else "(empty)"
            hand_summary = ",".join(c.label for c in current.hand)
            rlog.debug(
                "bot step=%d pid=%s name=%s pile_top=%s hand=[%s] active=%s",
                step,
                current.pid,
                current.name,
                top,
                hand_summary,
                (
                    self.game.active_source(current).value
                    if self.game.active_source(current)
                    else "none"
                ),
            )
            self.touch()
            await asyncio.sleep(AI_THINK_SECONDS)
            decision = decide(self.game, current, rng=rng)
            rlog.info(
                "bot decision pid=%s name=%s action=%s source=%s indices=%s",
                current.pid,
                current.name,
                decision.action,
                decision.source.value if decision.source else None,
                decision.indices,
            )
            try:
                if decision.action == "pickup":
                    result = self.game.pickup(current.pid)
                else:
                    assert decision.source is not None and decision.indices is not None
                    result = self.game.play(current.pid, decision.source, decision.indices)
                if not result.ok:
                    rlog.warning(
                        "bot action rejected pid=%s error=%r — forcing pickup",
                        current.pid,
                        result.error,
                    )
                    result = self.game.pickup(current.pid)
                    if not result.ok:
                        rlog.error(
                            "bot pickup also failed pid=%s error=%r — aborting",
                            current.pid,
                            result.error,
                        )
                        return
            except Exception:  # pylint: disable=broad-exception-caught
                rlog.exception("bot crashed pid=%s — forcing pickup", current.pid)
                self.game.pickup(current.pid)
            rlog.info(
                "bot action result pid=%s burned=%s picked_up=%s same_again=%s "
                "finished=%s game_over=%s",
                current.pid,
                result.burned,
                result.picked_up,
                result.same_player_again,
                result.finished_pid,
                result.game_over,
            )
            await self.broadcast_state()
        rlog.error(
            "bot loop hit %d-step lifetime backstop; halting",
            BOT_CAP_BOTS_ONLY,
        )


class RoomRegistry:
    def __init__(self) -> None:
        self._rooms: dict[str, Room] = {}
        self._lock = asyncio.Lock()

    async def create(self, host_pid: str, host_name: str) -> Room:
        async with self._lock:
            for _ in range(20):
                code = _new_code()
                if code not in self._rooms:
                    break
            else:
                raise RuntimeError("failed to allocate room code")
            room = Room(code=code, host_pid=host_pid)
            room.seats.append(Seat(pid=host_pid, name=host_name))
            self._rooms[code] = room
            return room

    def get(self, code: str) -> Room | None:
        return self._rooms.get(code.upper())

    def __len__(self) -> int:
        return len(self._rooms)

    async def remove(self, code: str) -> None:
        async with self._lock:
            self._rooms.pop(code, None)

    def evict_idle(self, timeout_seconds: float, now: float | None = None) -> list[str]:
        """Drop rooms with all sockets disconnected for longer than the timeout.

        Returns the list of evicted room codes.
        """
        clock = time.monotonic() if now is None else now
        evicted: list[str] = []
        for code, room in list(self._rooms.items()):
            if any(seat.socket is not None for seat in room.seats):
                continue
            if clock - room.last_activity_ts <= timeout_seconds:
                continue
            del self._rooms[code]
            evicted.append(code)
        return evicted


REGISTRY = RoomRegistry()


def parse_source(value: str) -> Source:
    try:
        return Source(value)
    except ValueError as exc:
        raise ValueError(f"unknown source: {value}") from exc
