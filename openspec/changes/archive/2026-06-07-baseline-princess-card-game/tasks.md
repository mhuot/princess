## 1. Project scaffolding

- [x] 1.1 Create `princess/` package, `tests/`, `static/`, `.venv/`
- [x] 1.2 Add `requirements.txt` / `requirements-dev.txt` (FastAPI, uvicorn, pydantic, pytest, pylint, black)
- [x] 1.3 Add Apache 2.0 `LICENSE` (Copyright 2026 Mike Huot)
- [x] 1.4 Add `.gitignore` (`.venv`, `__pycache__`, `.pytest_cache`)
- [x] 1.5 Add `pyproject.toml` configuring black (line 100), pylint, and pytest

## 2. Game engine — implements `game-engine`

- [x] 2.1 Implement `Card` dataclass and `make_deck()` returning 52 distinct cards
- [x] 2.2 Implement `Player` dataclass with `hand`, `face_up`, `face_down`, `choose`, `finished`, `ready`
- [x] 2.3 Implement `GameConfig` dataclass with `seven_on_seven=True` default and `from_dict` shim
- [x] 2.4 Implement `Game.__init__` with `swap_phase` flag selecting deal path
- [x] 2.5 Implement `_deal()` (test mode) and `_deal_with_swap()` (setup mode)
- [x] 2.6 Implement `set_face_up()`; transition to `playing` once everyone is `ready`
- [x] 2.7 Implement `is_legal_rank()` honoring 2-wild, 10-wild, 7-under, and 7-on-7 toggle
- [x] 2.8 Implement `play()` covering same-rank multi-card, index validation, face-down branch
- [x] 2.9 Implement face-down legality check + force-pickup of pile + revealed
- [x] 2.10 Implement burn effects (10 immediate, four-of-a-kind on top of pile)
- [x] 2.11 Implement hand refill from deck after every play
- [x] 2.12 Implement `pickup()` and turn advancement skipping finished players
- [x] 2.13 Implement `public_state()` and `view_for(pid)` hiding opponent hand identities
- [x] 2.14 Implement `_choose_starter()` (lowest hand card, excluding 2s and 10s)
- [x] 2.15 Implement game-over detection and `finished_order` appending

## 3. AI bot — implements `ai-bot`

- [x] 3.1 Implement `decide(game, player)` returning play or pickup
- [x] 3.2 Prefer the lowest legal non-special rank in hand
- [x] 3.3 Complete a 4-of-a-kind burn when the pile top + hand allows
- [x] 3.4 Use 10 (preferred) or 2 only when no non-special legal play exists
- [x] 3.5 Blind-random pick when active source is face-down
- [x] 3.6 Auto-pick top-3 highest ranks for face-up during swap phase in `Room.start_game()`
- [x] 3.7 `Room.run_bots()` async loop running until human or game-over
- [x] 3.8 30-action safety cap with `ERROR` log on exit
- [x] 3.9 Force-pickup fallback when engine rejects bot's action
- [x] 3.10 Catch unhandled exceptions during a bot turn and force pickup

## 4. Server — implements `room-server`

- [x] 4.1 Set up FastAPI app and static mount at `/static/`
- [x] 4.2 Implement `RoomRegistry` and `Room` with `asyncio.Lock`
- [x] 4.3 4-char alphanumeric `_new_code()` with uniqueness guard
- [x] 4.4 `POST /api/rooms` (create) returning code + pid
- [x] 4.5 `POST /api/rooms/{code}/join` with 404 / 409 errors
- [x] 4.6 `POST /api/rooms/{code}/bot` host-only with random bot name (no in-room duplicates)
- [x] 4.7 `POST /api/rooms/{code}/config` host-only, lobby-only, parse via `GameConfig.from_dict`
- [x] 4.8 `POST /api/rooms/{code}/start` host-only, ≥2 seats, auto-pick bot face-up
- [x] 4.9 `POST /api/rooms/{code}/rematch` host-only, requires game-over
- [x] 4.10 `POST /api/rooms/{code}/abort` host-only; reset `room.game = None`
- [x] 4.11 `POST /api/rooms/{code}/leave` host-forbidden
- [x] 4.12 `WS /ws/{code}/{pid}` lifecycle: initial sync, message loop, disconnect cleanup
- [x] 4.13 Message handler routes `play`, `pickup`, `set_face_up` and runs bot loop afterward
- [x] 4.14 Per-room broadcast distinguishing `lobby` vs `state` messages
- [x] 4.15 Ship 100-name SFW bot-name roster in `princess/bot_names.py`
- [x] 4.16 `pick_bot_name(taken)` fallback to `Bot <4-digit>` when pool is exhausted
- [x] 4.17 `python -m princess` entry-point invoking `setup_logging()` + `uvicorn.run`

## 5. Frontend — implements `web-frontend`

- [x] 5.1 `static/index.html` skeleton with lobby, setup, game, and game-over sections
- [x] 5.2 WCAG AAA color palette in `static/styles.css` (≥7:1 contrast)
- [x] 5.3 Lobby form with create / join, inline error banner
- [x] 5.4 Seat list with host / bot / offline badges
- [x] 5.5 House-rules config panel (host-editable; non-host disabled with note)
- [x] 5.6 Setup phase: 3 face-down placeholders + 6 selectable choose cards + lock-in button
- [x] 5.7 Replace-oldest selection logic when user picks a 4th setup card
- [x] 5.8 Opponent row with mini face-up/face-down and current-turn highlight
- [x] 5.9 Pile area with deck count, top card, dynamic rule indicator
- [x] 5.10 Collapsible "Special cards & house rules" legend re-rendered per state
- [x] 5.11 Your-table mini-row between "Your cards" heading and "Playing from:" status
- [x] 5.12 Full-size hand row with legal-play green outline and gold ★ on specials
- [x] 5.13 Hover tooltip on every card (rule reminder for 2 / 7 / 10)
- [x] 5.14 Toggle selection ensuring all selected cards share a rank
- [x] 5.15 Sort hand button preserving server-side indices for clicks
- [x] 5.16 Hide hand UI (heading, toolbar, row) when hand is empty
- [x] 5.17 Game-over panel hiding the play surface; rematch + back-to-lobby buttons
- [x] 5.18 Quit & return to lobby button (host abort / non-host leave)
- [x] 5.19 Logs viewer `static/logs.html` with live tail, autoscroll, download, clear
- [x] 5.20 Skip link, ARIA roles, focus outlines, `prefers-reduced-motion` respect

## 6. Logging — implements `logging`

- [x] 6.1 Implement `RingBufferHandler` (`collections.deque(maxlen=2000)`) with thread lock
- [x] 6.2 `snapshot(since, limit)` returning `(entries, last_id)` for paginated reads
- [x] 6.3 `dump_text()` for download endpoint
- [x] 6.4 `clear()` for the DELETE endpoint
- [x] 6.5 `setup_logging()` idempotent root-logger configuration (stdout + buffer)
- [x] 6.6 `room_logger(code)` returning `logging.getLogger("princess.room.<code>")`
- [x] 6.7 Instrument server endpoints (create / join / bot / config / start / rematch / abort / leave)
- [x] 6.8 Instrument WebSocket connect, disconnect, and crash paths
- [x] 6.9 Instrument every play, pickup, set_face_up — success and rejection
- [x] 6.10 Instrument bot decisions (pile top, hand, decision, result)
- [x] 6.11 Instrument bot safety cap and force-pickup fallback
- [x] 6.12 `GET /api/logs?since=&limit=` paginated read
- [x] 6.13 `GET /api/logs/download` text attachment with `Content-Disposition`
- [x] 6.14 `DELETE /api/logs` clears buffer and logs the clear

## 7. Tests

- [x] 7.1 `tests/test_game.py` covering deck, deal, legality, special cards, 7-under, four-of-a-kind, pickup, refill, source transitions, face-down legal + illegal, finish, view scoping
- [x] 7.2 `tests/test_ai.py` covering lowest-non-special preference, special-only fallback, 4-of-kind completion, 7-under obedience, full AI-vs-AI termination
- [x] 7.3 `tests/test_server.py` covering create + join, missing-room 404, host-only enforcement, full WebSocket round-trip from lobby → start → state
- [x] 7.4 (Follow-on) Tests for the swap-phase `set_face_up` path
- [x] 7.5 (Follow-on) Tests for the config / abort / rematch / leave endpoints
- [x] 7.6 (Follow-on) Tests for the logging buffer + endpoints

## 8. OpenSpec baseline (this change)

- [x] 8.1 Write `proposal.md`
- [x] 8.2 Write `design.md`
- [x] 8.3 Write `specs/game-engine/spec.md`
- [x] 8.4 Write `specs/ai-bot/spec.md`
- [x] 8.5 Write `specs/room-server/spec.md`
- [x] 8.6 Write `specs/web-frontend/spec.md`
- [x] 8.7 Write `specs/logging/spec.md`
- [x] 8.8 Write `tasks.md` (this file)
- [x] 8.9 Review specs with stakeholder (Mike) and archive change via `/opsx:archive`
