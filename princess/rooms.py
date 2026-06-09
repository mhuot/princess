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
import json
import logging
import random
import secrets
import sqlite3
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

# --- persistence -------------------------------------------------------------
DEFAULT_DB_PATH = "./princess.db"
_SCHEMA_VERSION = 1
CREATE_TABLE_SQL = (
    "CREATE TABLE IF NOT EXISTS rooms ("
    "code TEXT PRIMARY KEY, "
    "payload TEXT NOT NULL, "
    "updated_ts REAL NOT NULL"
    ")"
)

_persist_log = logging.getLogger("princess.persistence")


def _new_code() -> str:
    return "".join(secrets.choice(ROOM_CODE_CHARS) for _ in range(ROOM_CODE_LEN))


@dataclass
class Seat:
    pid: str
    name: str
    is_bot: bool = False
    socket: WebSocket | None = None


def _fresh_scoreboard_entry() -> dict[str, int]:
    """A zeroed session-scoreboard entry for a single seat."""
    return {"princess_wins": 0, "last_places": 0, "rounds_played": 0}


@dataclass
class Room:
    code: str
    host_pid: str
    seats: list[Seat] = field(default_factory=list)
    game: Game | None = None
    config: GameConfig = field(default_factory=GameConfig)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    last_activity_ts: float = field(default_factory=time.monotonic)
    # Session-level scoreboard. Keyed by seat.pid; survives `/rematch` and
    # zeros on `/abort`. Entries are added on seat creation and dropped on
    # seat removal (see `_ensure_scoreboard_entry` / `_drop_scoreboard_entry`).
    scoreboard: dict[str, dict[str, int]] = field(default_factory=dict)
    # `id()` of the last `Game` whose game-over bump has already been applied.
    # Cleared in `start_game()` so each new round can bump exactly once when it
    # ends. Used by `_bump_scoreboard_if_needed()` to stay idempotent across
    # reconnect-driven re-broadcasts.
    _scoreboard_counted_for_game: int | None = None

    def touch(self) -> None:
        """Mark the room as recently active so the idle sweep spares it."""
        self.last_activity_ts = time.monotonic()

    def seat_by_pid(self, pid: str) -> Seat | None:
        for seat in self.seats:
            if seat.pid == pid:
                return seat
        return None

    def _ensure_scoreboard_entry(self, pid: str) -> None:
        """Add a zeroed scoreboard entry for ``pid`` if absent."""
        if pid not in self.scoreboard:
            self.scoreboard[pid] = _fresh_scoreboard_entry()

    def _drop_scoreboard_entry(self, pid: str) -> None:
        """Remove ``pid`` from the scoreboard; no-op if absent."""
        self.scoreboard.pop(pid, None)

    def _bump_scoreboard_if_needed(self) -> None:
        """Increment counters when the current `Game` has just finished.

        Idempotent: a re-broadcast of the same finished `Game` does not double
        count thanks to the `_scoreboard_counted_for_game` marker, which is
        cleared on every fresh `start_game()`.
        """
        game = self.game
        if game is None or not game.game_over:
            return
        if self._scoreboard_counted_for_game == id(game):
            return
        finished_order = list(game.finished_order)
        if finished_order:
            winner_pid = finished_order[0]
            last_pid = finished_order[-1]
            if winner_pid in self.scoreboard:
                self.scoreboard[winner_pid]["princess_wins"] += 1
            if last_pid in self.scoreboard:
                self.scoreboard[last_pid]["last_places"] += 1
            for pid in finished_order:
                if pid in self.scoreboard:
                    self.scoreboard[pid]["rounds_played"] += 1
        self._scoreboard_counted_for_game = id(game)

    def reset_scoreboard(self) -> None:
        """Zero every existing entry without dropping any (used by `/abort`)."""
        for pid in self.scoreboard:
            self.scoreboard[pid] = _fresh_scoreboard_entry()

    # ---- persistence -----------------------------------------------------

    def to_dict(self) -> dict:
        """Serialize the room to a JSON-friendly dict for SQLite storage.

        Sockets are dropped (they live in the old process's TCP stack), and
        ``last_activity_ts`` (a ``time.monotonic()`` reading) is translated to
        wall-clock so the value survives a restart.
        """
        wall_last_activity_ts = time.time() - (time.monotonic() - self.last_activity_ts)
        return {
            "schema_version": _SCHEMA_VERSION,
            "code": self.code,
            "host_pid": self.host_pid,
            "seats": [{"pid": s.pid, "name": s.name, "is_bot": s.is_bot} for s in self.seats],
            "config": self.config.to_dict(),
            "game": self.game.to_dict() if self.game is not None else None,
            "scoreboard": {pid: dict(entry) for pid, entry in self.scoreboard.items()},
            "scoreboard_counted_for_game": self._scoreboard_counted_for_game,
            "wall_last_activity_ts": wall_last_activity_ts,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Room":
        """Reconstruct a room from a ``to_dict`` payload.

        Sockets are ``None`` on every seat (clients reconnect themselves), a
        fresh ``asyncio.Lock`` is constructed by the dataclass default factory,
        and ``last_activity_ts`` is rebased onto the new process's monotonic
        clock so idle eviction continues to behave correctly.
        """
        version = data.get("schema_version")
        if version != _SCHEMA_VERSION:
            raise ValueError(
                f"unsupported room schema_version: {version!r}" f" (expected {_SCHEMA_VERSION})"
            )
        seats = [
            Seat(pid=str(s["pid"]), name=str(s["name"]), is_bot=bool(s["is_bot"]))
            for s in data.get("seats", [])
        ]
        wall = float(data.get("wall_last_activity_ts", time.time()))
        last_activity_ts = time.monotonic() - max(0.0, time.time() - wall)
        room = cls(
            code=str(data["code"]),
            host_pid=str(data["host_pid"]),
            seats=seats,
            game=Game.from_dict(data["game"]) if data.get("game") is not None else None,
            config=GameConfig.from_dict(data.get("config")),
            last_activity_ts=last_activity_ts,
        )
        scoreboard_raw = data.get("scoreboard", {}) or {}
        room.scoreboard = {
            str(pid): {
                "princess_wins": int(entry.get("princess_wins", 0)),
                "last_places": int(entry.get("last_places", 0)),
                "rounds_played": int(entry.get("rounds_played", 0)),
            }
            for pid, entry in scoreboard_raw.items()
        }
        # The idempotency marker stored the previous process's ``id(game)``,
        # which is meaningless here. If the saved game had already been counted
        # (marker non-None) and is still game-over, rebind the marker to the
        # freshly-loaded ``Game`` instance so the next broadcast does not
        # double-count. Otherwise leave it ``None``.
        counted = data.get("scoreboard_counted_for_game")
        if counted is not None and room.game is not None and room.game.game_over:
            # pylint: disable=protected-access
            room._scoreboard_counted_for_game = id(room.game)
        else:
            # pylint: disable=protected-access
            room._scoreboard_counted_for_game = None
        return room

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
            "scoreboard": {pid: dict(entry) for pid, entry in self.scoreboard.items()},
        }

    async def broadcast_lobby(self) -> None:
        msg = {"type": "lobby", "room": self.public_lobby()}
        await self._broadcast(msg)

    async def broadcast_state(self) -> None:
        # Game-over bumps fire at the room layer (engine stays pure). The
        # bump is idempotent so re-broadcasts on reconnect do not double-count.
        self._bump_scoreboard_if_needed()
        if self.game is None:
            await self.broadcast_lobby()
            return
        bot_pids = {s.pid for s in self.seats if s.is_bot}
        scoreboard = {pid: dict(entry) for pid, entry in self.scoreboard.items()}
        for seat in self.seats:
            if seat.is_bot or seat.socket is None:
                continue
            view = self.game.view_for(seat.pid, bot_pids=bot_pids)
            await self._send(
                seat.socket,
                {"type": "state", "view": view, "scoreboard": scoreboard},
            )

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
        # A fresh game means the next game-over bump must fire. Clearing the
        # marker here (rather than at game-over) makes rematches naturally
        # countable without any extra wiring.
        self._scoreboard_counted_for_game = None
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
            await REGISTRY.persist(self)
        rlog.error(
            "bot loop hit %d-step lifetime backstop; halting",
            BOT_CAP_BOTS_ONLY,
        )


class RoomRegistry:
    def __init__(self, db_path: str | None = None) -> None:
        self._rooms: dict[str, Room] = {}
        self._lock = asyncio.Lock()
        self._db_path: str | None = db_path
        self._conn: sqlite3.Connection | None = None
        if db_path is not None:
            self._conn = self._open_db(db_path)

    # ---- SQLite plumbing -------------------------------------------------

    @staticmethod
    def _open_db(path: str) -> sqlite3.Connection:
        """Open a SQLite connection in autocommit + WAL mode."""
        conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        # WAL keeps readers unblocked by writers. ``journal_mode`` returns a row.
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(CREATE_TABLE_SQL)
        return conn

    def attach_db(self, path: str) -> None:
        """Open the DB and bind it to this registry. Idempotent on path."""
        if self._conn is not None:
            self._conn.close()
        self._db_path = path
        self._conn = self._open_db(path)

    async def persist(self, room: Room) -> None:
        """Upsert the room's serialized state. Errors are logged, not raised."""
        if self._conn is None:
            return
        try:
            payload = json.dumps(room.to_dict())
        except (TypeError, ValueError):
            _persist_log.exception(
                "failed to serialize room code=%s; in-memory state unchanged",
                room.code,
            )
            return
        try:
            await asyncio.to_thread(self._persist_sync, room.code, payload)
        except sqlite3.Error:
            _persist_log.exception(
                "sqlite write failed for room code=%s; in-memory state unchanged",
                room.code,
            )

    def _persist_sync(self, code: str, payload: str) -> None:
        assert self._conn is not None
        self._conn.execute(
            "INSERT OR REPLACE INTO rooms (code, payload, updated_ts) VALUES (?, ?, ?)",
            (code, payload, time.time()),
        )

    async def forget(self, code: str) -> None:
        """Delete the row for ``code``. Errors logged, not raised."""
        if self._conn is None:
            return
        try:
            await asyncio.to_thread(self._forget_sync, code)
        except sqlite3.Error:
            _persist_log.exception("sqlite delete failed for room code=%s", code)

    def _forget_sync(self, code: str) -> None:
        assert self._conn is not None
        self._conn.execute("DELETE FROM rooms WHERE code = ?", (code,))

    def restore_all(self) -> int:
        """Load every persisted room into ``self._rooms``.

        Best-effort: rows with malformed JSON or schema mismatches are logged
        and skipped so a single bad row never blocks startup. Returns the count
        of successfully restored rooms.
        """
        if self._conn is None:
            return 0
        try:
            rows = list(self._conn.execute("SELECT code, payload FROM rooms"))
        except sqlite3.Error:
            _persist_log.exception("sqlite read failed; starting with empty registry")
            return 0
        restored = 0
        for code, payload in rows:
            try:
                data = json.loads(payload)
                room = Room.from_dict(data)
            except (json.JSONDecodeError, KeyError, ValueError, TypeError):
                _persist_log.exception("skipping corrupt room row code=%s", code)
                continue
            self._rooms[room.code] = room
            restored += 1
            _persist_log.info("restored room code=%s seats=%d", room.code, len(room.seats))
        return restored

    # ---- room lifecycle --------------------------------------------------

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
            room._ensure_scoreboard_entry(host_pid)  # pylint: disable=protected-access
            self._rooms[code] = room
        await self.persist(room)
        return room

    def get(self, code: str) -> Room | None:
        return self._rooms.get(code.upper())

    def __len__(self) -> int:
        return len(self._rooms)

    async def remove(self, code: str) -> None:
        async with self._lock:
            self._rooms.pop(code, None)
        await self.forget(code)

    def evict_idle(self, timeout_seconds: float, now: float | None = None) -> list[str]:
        """Drop rooms with all sockets disconnected for longer than the timeout.

        Returns the list of evicted room codes. Each evicted code is also
        deleted from the SQLite store (sync, errors logged not raised).
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
        if self._conn is not None:
            for code in evicted:
                try:
                    self._forget_sync(code)
                except sqlite3.Error:
                    _persist_log.exception("sqlite delete failed during eviction for code=%s", code)
        return evicted


REGISTRY = RoomRegistry()


def parse_source(value: str) -> Source:
    try:
        return Source(value)
    except ValueError as exc:
        raise ValueError(f"unknown source: {value}") from exc
