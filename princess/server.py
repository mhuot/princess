#!/usr/bin/env python3
"""
FastAPI server for Princess Card Game.

Endpoints:
  GET  /                         — serves the lobby HTML
  POST /api/rooms                — create a room, returns code + your pid
  POST /api/rooms/{code}/join    — claim a seat in an existing room
  POST /api/rooms/{code}/bot     — host adds a bot to an open seat
  POST /api/rooms/{code}/start   — host starts the game
  WS   /ws/{code}/{pid}          — gameplay socket; one per seated player

Copyright 2026 Mike Huot

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0
"""

from __future__ import annotations

import logging
import os
import secrets
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded

from .bot_names import pick_bot_name
from .game import GameConfig
from .logging_config import LOG_BUFFER, room_logger, setup_logging
from .rooms import DEFAULT_DB_PATH, MAX_PLAYERS, MIN_PLAYERS, REGISTRY, Seat, parse_source

ROOM_IDLE_TIMEOUT = float(os.environ.get("ROOM_IDLE_TIMEOUT_SECONDS", "300"))

# Per-IP rate-limit quotas for the four mutating room endpoints. Sized so legit
# human use (double-clicks, retries) is never throttled but scripted floods are.
RATE_LIMIT_CREATE = "6/minute"
RATE_LIMIT_JOIN = "30/minute"
RATE_LIMIT_BOT = "20/minute"
RATE_LIMIT_RENAME = "30/minute"
RATE_LIMIT_LEADERBOARD = "60/minute"

LEADERBOARD_MAX_LIMIT = 200
LEADERBOARD_DEFAULT_LIMIT = 50
LEADERBOARD_DEFAULT_MIN_ROUNDS = 5
LEADERBOARD_CACHE_TTL = 5.0
LEADERBOARD_SORTS = ("wins", "winrate", "rounds")


def _client_ip(request: Request) -> str:
    """Return the real client IP, honoring the nginx-set X-Forwarded-For header.

    The first entry in XFF is the original client; subsequent entries are
    intermediate proxies. When XFF is absent (e.g. direct local calls), we fall
    back to ``request.client.host``. As a last-ditch safety net (no socket peer
    info either), return ``"unknown"`` so all such requests share one bucket
    rather than crashing the key function.
    """
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",", 1)[0].strip()
    if request.client is not None:
        return request.client.host
    return "unknown"


limiter = Limiter(key_func=_client_ip)
if os.environ.get("PRINCESS_RATE_LIMIT_DISABLED") == "1":
    limiter.enabled = False


def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Return 429 with ``{"detail": ...}`` to match the rest of the API.

    slowapi's default handler emits ``{"error": ...}``, but every other error
    on this server uses FastAPI's ``HTTPException`` shape (``{"detail": ...}``)
    and the desktop + mobile error helpers read ``detail`` verbatim. Keep the
    contract uniform here so the existing toasts render the quota string.
    """
    del request  # signature required by Starlette exception-handler protocol
    return JSONResponse(
        status_code=429,
        content={"detail": f"rate limit exceeded: {exc.detail}"},
    )


APP_STARTED_AT = time.monotonic()


def _sweep_idle_rooms() -> None:
    evicted = REGISTRY.evict_idle(ROOM_IDLE_TIMEOUT)
    for code in evicted:
        log.info("evicted idle room code=%s", code)


setup_logging()
log = logging.getLogger("princess.server")

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(app_: FastAPI):
    """Open the SQLite store and restore any persisted rooms on startup."""
    del app_  # FastAPI passes the app; we only need REGISTRY.
    db_path = os.environ.get("PRINCESS_DB_PATH", DEFAULT_DB_PATH)
    REGISTRY.attach_db(db_path)
    count = REGISTRY.restore_all()
    log.info("restored %d rooms from %s", count, db_path)
    yield


app = FastAPI(title="Princess Card Game", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class CreateRoomBody(BaseModel):
    name: str = Field(min_length=1, max_length=20)


class JoinRoomBody(BaseModel):
    name: str = Field(min_length=1, max_length=20)


class AddBotBody(BaseModel):
    host_pid: str


class StartBody(BaseModel):
    host_pid: str


class ConfigBody(BaseModel):
    host_pid: str
    config: dict


def _new_pid() -> str:
    return secrets.token_urlsafe(8)


def _wants_mobile_redirect(request: Request) -> bool:
    """True iff a desktop route should 302 to its /m equivalent."""
    if request.query_params.get("desktop") == "1":
        return False
    if request.cookies.get("princess_prefer_desktop") == "1":
        return False
    return "Mobi" in request.headers.get("user-agent", "")


@app.get("/")
async def index(request: Request):
    if _wants_mobile_redirect(request):
        return RedirectResponse("/m", status_code=302)
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/room/{code}")
async def room_page(request: Request, code: str):  # pylint: disable=unused-argument
    if _wants_mobile_redirect(request):
        return RedirectResponse(f"/m/{code}", status_code=302)
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/m")
async def mobile_index() -> FileResponse:
    return FileResponse(STATIC_DIR / "mobile.html")


@app.get("/m/{code}")
async def mobile_room_page(code: str) -> FileResponse:  # pylint: disable=unused-argument
    return FileResponse(STATIC_DIR / "mobile.html")


@app.get("/healthz")
async def healthz() -> dict:
    return {
        "status": "ok",
        "uptime_seconds": int(time.monotonic() - APP_STARTED_AT),
        "rooms": len(REGISTRY),
        "log_buffer_size": len(LOG_BUFFER),
    }


@app.get("/logs")
async def logs_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "logs.html")


@app.get("/leaderboard")
async def leaderboard_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "leaderboard.html")


class _LeaderboardCache:
    """Tiny in-process TTL cache keyed by (limit, sort, min_rounds)."""

    def __init__(self, ttl: float) -> None:
        self._ttl = ttl
        self._store: dict[tuple[int, str, int], tuple[float, list[dict]]] = {}

    def get(self, key: tuple[int, str, int]) -> list[dict] | None:
        hit = self._store.get(key)
        if hit is None:
            return None
        cached_at, value = hit
        if time.monotonic() - cached_at > self._ttl:
            self._store.pop(key, None)
            return None
        return value

    def put(self, key: tuple[int, str, int], value: list[dict]) -> None:
        self._store[key] = (time.monotonic(), value)

    def clear(self) -> None:
        self._store.clear()


_LEADERBOARD_CACHE = _LeaderboardCache(LEADERBOARD_CACHE_TTL)


@app.get("/api/leaderboard")
@limiter.limit(RATE_LIMIT_LEADERBOARD)
async def get_leaderboard(
    request: Request,
    limit: int = LEADERBOARD_DEFAULT_LIMIT,
    sort: str = "wins",
    min_rounds: int = LEADERBOARD_DEFAULT_MIN_ROUNDS,
) -> dict:
    del request  # used by slowapi for key extraction
    if limit < 1 or limit > LEADERBOARD_MAX_LIMIT:
        raise HTTPException(400, f"limit must be between 1 and {LEADERBOARD_MAX_LIMIT}")
    if sort not in LEADERBOARD_SORTS:
        raise HTTPException(400, f"sort must be one of {', '.join(LEADERBOARD_SORTS)}")
    if min_rounds < 0:
        raise HTTPException(400, "min_rounds must be >= 0")
    cache_min_rounds = min_rounds if sort == "winrate" else 0
    key = (limit, sort, cache_min_rounds)
    cached = _LEADERBOARD_CACHE.get(key)
    if cached is None:
        entries = REGISTRY.read_leaderboard(limit=limit, sort=sort, min_rounds=min_rounds)
        _LEADERBOARD_CACHE.put(key, entries)
    else:
        entries = cached
    return {"entries": entries, "generated_ts": time.time()}


@app.get("/api/logs")
async def get_logs(since: int = 0, limit: int = 500) -> dict:
    entries, last_id = LOG_BUFFER.snapshot(since=since, limit=limit)
    return {"entries": entries, "last_id": last_id, "capacity": LOG_BUFFER.capacity}


@app.get("/api/logs/download")
async def download_logs() -> PlainTextResponse:
    body = LOG_BUFFER.dump_text() or "(log buffer is empty)\n"
    return PlainTextResponse(
        body,
        headers={"Content-Disposition": 'attachment; filename="princess.log"'},
    )


@app.delete("/api/logs")
async def clear_logs() -> dict:
    LOG_BUFFER.clear()
    log.info("log buffer cleared by user")
    return {"ok": True}


def _name_already_taken(
    room, name: str, *, exclude_pid: str | None = None
) -> tuple[bool, str | None]:
    """Case-insensitive, whitespace-trimmed dedupe check.

    Returns (True, existing_name) when a conflict exists, where existing_name
    is the casing of the existing seat (for the error message). Returns
    (False, None) otherwise.
    """
    needle = name.strip().casefold()
    for s in room.seats:
        if s.pid == exclude_pid:
            continue
        if s.name.strip().casefold() == needle:
            return True, s.name
    return False, None


@app.post("/api/rooms")
@limiter.limit(RATE_LIMIT_CREATE)
async def create_room(request: Request, body: CreateRoomBody) -> dict:
    del request  # used by slowapi for key extraction
    _sweep_idle_rooms()
    name = body.name.strip()
    pid = _new_pid()
    # ``REGISTRY.create`` already persists the freshly-created room.
    room = await REGISTRY.create(host_pid=pid, host_name=name)
    log.info("room created code=%s host=%s pid=%s", room.code, name, pid)
    room_logger(room.code).info("room opened by host=%s pid=%s", name, pid)
    return {"code": room.code, "pid": pid}


@app.post("/api/rooms/{code}/join")
@limiter.limit(RATE_LIMIT_JOIN)
async def join_room(request: Request, code: str, body: JoinRoomBody) -> dict:
    del request  # used by slowapi for key extraction
    _sweep_idle_rooms()
    room = REGISTRY.get(code)
    if room is None:
        raise HTTPException(404, "room not found")
    if room.game is not None:
        raise HTTPException(409, "game already started")
    if len(room.seats) >= MAX_PLAYERS:
        raise HTTPException(409, "room full")
    name = body.name.strip()
    taken, existing = _name_already_taken(room, name)
    if taken:
        raise HTTPException(409, f"name '{existing}' is already taken in this room")
    pid = _new_pid()
    room.seats.append(Seat(pid=pid, name=name))
    room._ensure_scoreboard_entry(pid)  # pylint: disable=protected-access
    room_logger(room.code).info("seat joined name=%s pid=%s seats=%d", name, pid, len(room.seats))
    await room.broadcast_lobby()
    await REGISTRY.persist(room)
    return {"code": room.code, "pid": pid}


@app.post("/api/rooms/{code}/bot")
@limiter.limit(RATE_LIMIT_BOT)
async def add_bot(request: Request, code: str, body: AddBotBody) -> dict:
    del request  # used by slowapi for key extraction
    room = REGISTRY.get(code)
    if room is None:
        raise HTTPException(404, "room not found")
    if room.host_pid != body.host_pid:
        raise HTTPException(403, "only the host can add bots")
    if room.game is not None:
        raise HTTPException(409, "game already started")
    if len(room.seats) >= MAX_PLAYERS:
        raise HTTPException(409, "room full")
    bot_pid = _new_pid()
    taken = {s.name for s in room.seats}
    bot_name = pick_bot_name(taken)
    room.seats.append(Seat(pid=bot_pid, name=bot_name, is_bot=True))
    room._ensure_scoreboard_entry(bot_pid)  # pylint: disable=protected-access
    room_logger(room.code).info(
        "bot added name=%r pid=%s seats=%d", bot_name, bot_pid, len(room.seats)
    )
    await room.broadcast_lobby()
    await REGISTRY.persist(room)
    return {"ok": True, "name": bot_name}


class RemoveBotBody(BaseModel):
    host_pid: str
    bot_pid: str


@app.post("/api/rooms/{code}/remove_bot")
async def remove_bot(code: str, body: RemoveBotBody) -> dict:
    room = REGISTRY.get(code)
    if room is None:
        raise HTTPException(404, "room not found")
    if room.host_pid != body.host_pid:
        raise HTTPException(403, "only the host can remove bots")
    if room.game is not None:
        raise HTTPException(409, "game already started")
    seat = room.seat_by_pid(body.bot_pid)
    if seat is None:
        raise HTTPException(404, "seat not found")
    if not seat.is_bot:
        raise HTTPException(409, "cannot remove a human seat")
    room.seats.remove(seat)
    room._drop_scoreboard_entry(seat.pid)  # pylint: disable=protected-access
    room_logger(room.code).info(
        "bot removed name=%r pid=%s remaining=%d", seat.name, seat.pid, len(room.seats)
    )
    await room.broadcast_lobby()
    await REGISTRY.persist(room)
    return {"ok": True}


class RenameBody(BaseModel):
    pid: str
    new_name: str = Field(min_length=1, max_length=20)


@app.post("/api/rooms/{code}/rename")
@limiter.limit(RATE_LIMIT_RENAME)
async def rename_seat(request: Request, code: str, body: RenameBody) -> dict:
    del request  # used by slowapi for key extraction
    room = REGISTRY.get(code)
    if room is None:
        raise HTTPException(404, "room not found")
    seat = room.seat_by_pid(body.pid)
    if seat is None:
        raise HTTPException(404, "seat not found")
    new_name = body.new_name.strip()
    # Rename-to-self (case-insensitive) is a no-op — no state change, no broadcast.
    if new_name.casefold() == seat.name.strip().casefold():
        return {"ok": True, "name": seat.name}
    taken, existing = _name_already_taken(room, new_name, exclude_pid=body.pid)
    if taken:
        raise HTTPException(409, f"name '{existing}' is already taken in this room")
    old_name = seat.name
    seat.name = new_name
    if room.game is not None:
        try:
            room.game.player(body.pid).name = new_name
        except KeyError:
            pass
    room_logger(room.code).info("seat renamed pid=%s old=%r new=%r", body.pid, old_name, new_name)
    if room.game is None:
        await room.broadcast_lobby()
    else:
        await room.broadcast_state()
    await REGISTRY.persist(room)
    return {"ok": True, "name": new_name}


@app.post("/api/rooms/{code}/config")
async def update_config(code: str, body: ConfigBody) -> dict:
    room = REGISTRY.get(code)
    if room is None:
        raise HTTPException(404, "room not found")
    if room.host_pid != body.host_pid:
        raise HTTPException(403, "only the host can change rules")
    if room.game is not None:
        raise HTTPException(409, "game already started")
    room.config = GameConfig.from_dict(body.config)
    room_logger(room.code).info("config updated %s", room.config.to_dict())
    await room.broadcast_lobby()
    await REGISTRY.persist(room)
    return {"ok": True, "config": room.config.to_dict()}


@app.post("/api/rooms/{code}/end_round")
async def end_round(code: str, body: StartBody) -> dict:
    """Host-only: declare the in-progress round done with current standings."""
    room = REGISTRY.get(code)
    if room is None:
        raise HTTPException(404, "room not found")
    if room.host_pid != body.host_pid:
        raise HTTPException(403, "only the host can end the round")
    if room.game is None:
        raise HTTPException(409, "no game in progress")
    if room.game.game_over:
        raise HTTPException(409, "game already over")
    async with room.lock:
        result = room.game.end_round()
        if not result.ok:
            raise HTTPException(409, result.error or "could not end round")
    room_logger(code).info("host ended round; finishing_order=%s", room.game.finished_order)
    await room.broadcast_state()
    await REGISTRY.persist(room)
    return {"ok": True}


@app.post("/api/rooms/{code}/abort")
async def abort_game(code: str, body: StartBody) -> dict:
    """Host-only: end the current game and drop the room back into the lobby."""
    room = REGISTRY.get(code)
    if room is None:
        raise HTTPException(404, "room not found")
    if room.host_pid != body.host_pid:
        raise HTTPException(403, "only the host can abort the game")
    if room.game is None:
        return {"ok": True}
    async with room.lock:
        room.reset_for_rematch()
        # `/abort` is the explicit "end the session" signal — pair the
        # scoreboard reset with it so the host gets a clean slate without
        # recreating the room. `/rematch` deliberately preserves counts.
        room.reset_scoreboard()
    room_logger(code).info("host aborted game; returning to lobby")
    await room.broadcast_lobby()
    await REGISTRY.persist(room)
    return {"ok": True}


class LeaveBody(BaseModel):
    pid: str
    convert_to_bot: bool = False


@app.post("/api/rooms/{code}/leave")
async def leave_room(code: str, body: LeaveBody) -> dict:
    room = REGISTRY.get(code)
    if room is None:
        raise HTTPException(404, "room not found")
    seat = room.seat_by_pid(body.pid)
    if seat is None:
        return {"ok": True}
    if seat.pid == room.host_pid:
        raise HTTPException(409, "host can't leave — use abort instead")
    rlog = room_logger(code)
    converted = False
    if body.convert_to_bot and room.game is not None and not room.game.game_over:
        seat.is_bot = True
        if seat.socket is not None:
            try:
                await seat.socket.close()
            except (RuntimeError, ConnectionError):
                pass
            seat.socket = None
        # If we're mid-setup, the new bot owes the room a face-up selection
        # before the deal can advance to "playing".
        if room.game.phase == "setup":
            room._auto_pick_bot_face_up(seat.pid)  # pylint: disable=protected-access
        converted = True
        rlog.info("seat converted to bot name=%s pid=%s", seat.name, seat.pid)
    else:
        room.seats.remove(seat)
        room._drop_scoreboard_entry(seat.pid)  # pylint: disable=protected-access
        rlog.info("seat left name=%s pid=%s remaining=%d", seat.name, seat.pid, len(room.seats))
    if room.game is None:
        await room.broadcast_lobby()
    else:
        await room.broadcast_state()
    await REGISTRY.persist(room)
    if converted:
        # New bot may now be current — drive its turn(s).
        await room.run_bots()
    return {"ok": True, "converted": converted}


@app.post("/api/rooms/{code}/rematch")
async def rematch(code: str, body: StartBody) -> dict:
    room = REGISTRY.get(code)
    if room is None:
        raise HTTPException(404, "room not found")
    if room.host_pid != body.host_pid:
        raise HTTPException(403, "only the host can start a rematch")
    if room.game is None or not room.game.game_over:
        raise HTTPException(409, "no finished game to rematch")
    async with room.lock:
        room.reset_for_rematch()
        room.start_game()
    room_logger(room.code).info("rematch started")
    await room.broadcast_state()
    await REGISTRY.persist(room)
    await room.run_bots()
    return {"ok": True}


@app.post("/api/rooms/{code}/start")
async def start_game(code: str, body: StartBody) -> dict:
    room = REGISTRY.get(code)
    if room is None:
        raise HTTPException(404, "room not found")
    if room.host_pid != body.host_pid:
        raise HTTPException(403, "only the host can start the game")
    if len(room.seats) < MIN_PLAYERS:
        raise HTTPException(409, f"need at least {MIN_PLAYERS} players")
    if room.game is not None:
        raise HTTPException(409, "already started")
    async with room.lock:
        room.start_game()
    room_logger(room.code).info(
        "game started seats=%d config=%s",
        len(room.seats),
        room.config.to_dict(),
    )
    await room.broadcast_state()
    await REGISTRY.persist(room)
    await room.run_bots()
    return {"ok": True}


@app.websocket("/ws/{code}/{pid}")
async def gameplay_socket(websocket: WebSocket, code: str, pid: str) -> None:
    await websocket.accept()
    room = REGISTRY.get(code)
    if room is None:
        await websocket.send_json({"type": "error", "message": "room not found"})
        # Code 4001 with reason="unknown_room" signals permanent rejection so
        # clients can distinguish a stale sentinel from a transient drop.
        await websocket.close(code=4001, reason="unknown_room")
        return
    seat = room.seat_by_pid(pid)
    if seat is None or seat.is_bot:
        await websocket.send_json({"type": "error", "message": "seat not found"})
        # Code 4001 with reason="unknown_pid" signals permanent rejection.
        await websocket.close(code=4001, reason="unknown_pid")
        return
    seat.socket = websocket
    room.touch()
    rlog = room_logger(code)
    rlog.info("ws connected pid=%s name=%s", pid, seat.name)
    try:
        # Initial sync.
        if room.game is None:
            await websocket.send_json({"type": "lobby", "room": room.public_lobby()})
            await room.broadcast_lobby()
        else:
            bot_pids = {s.pid for s in room.seats if s.is_bot}
            await websocket.send_json(
                {"type": "state", "view": room.game.view_for(pid, bot_pids=bot_pids)}
            )

        while True:
            msg = await websocket.receive_json()
            await _handle_message(room, seat, msg)
    except WebSocketDisconnect:
        rlog.info("ws disconnected pid=%s name=%s", pid, seat.name)
    except Exception:  # pylint: disable=broad-exception-caught
        rlog.exception("ws handler crashed pid=%s name=%s", pid, seat.name)
    finally:
        seat.socket = None
        if room.game is None:
            await room.broadcast_lobby()


async def _handle_message(room, seat: Seat, msg: dict) -> None:
    kind = msg.get("type")
    rlog = room_logger(room.code)
    if room.game is None:
        rlog.warning("message before game start kind=%s pid=%s", kind, seat.pid)
        await seat.socket.send_json({"type": "error", "message": "game not started"})
        return
    room.touch()
    async with room.lock:
        if kind == "play":
            source = parse_source(msg["source"])
            indices = [int(i) for i in msg["indices"]]
            rlog.info(
                "ws play pid=%s name=%s source=%s indices=%s",
                seat.pid,
                seat.name,
                source.value,
                indices,
            )
            result = room.game.play(seat.pid, source, indices)
        elif kind == "pickup":
            rlog.info("ws pickup pid=%s name=%s", seat.pid, seat.name)
            result = room.game.pickup(seat.pid)
        elif kind == "set_face_up":
            indices = [int(i) for i in msg["indices"]]
            rlog.info("ws set_face_up pid=%s name=%s indices=%s", seat.pid, seat.name, indices)
            result = room.game.set_face_up(seat.pid, indices)
        else:
            rlog.warning("unknown message kind=%s pid=%s", kind, seat.pid)
            await seat.socket.send_json({"type": "error", "message": f"unknown type: {kind}"})
            return
        if not result.ok:
            rlog.warning("action rejected pid=%s kind=%s error=%s", seat.pid, kind, result.error)
            await seat.socket.send_json({"type": "error", "message": result.error})
        else:
            rlog.info(
                "action ok kind=%s burned=%s picked_up=%s same_again=%s finished=%s game_over=%s",
                kind,
                result.burned,
                result.picked_up,
                result.same_player_again,
                result.finished_pid,
                result.game_over,
            )
    await room.broadcast_state()
    if result.ok:
        await REGISTRY.persist(room)
    await room.run_bots()
