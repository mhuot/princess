## Purpose

The `room-server` capability is Princess's FastAPI HTTP + WebSocket front door. It owns an in-memory room registry, the room lifecycle (create / join / add-bot / config / start / rematch / abort / leave), the WebSocket play/pickup/set_face_up message protocol, host-only authorization, the bot-name pool, and the four-character room code namespace. All state lives in process memory; a restart forgets every room.

## Requirements

### Requirement: Room creation

The server SHALL expose `POST /api/rooms` accepting `{"name": <string 1–20 chars>}`. On success it SHALL allocate a fresh 4-character alphanumeric room code (A–Z, 0–9), create a `Room` whose host is the caller, and return `{"code": <code>, "pid": <opaque id>}`.

#### Scenario: Code is unique within active rooms

- **WHEN** `POST /api/rooms` is called
- **THEN** the returned `code` does not collide with any existing room in the registry

#### Scenario: Host seat is recorded

- **WHEN** a room is created
- **THEN** the registry's room contains exactly one seat whose `pid == host_pid` and `is_bot == False`

### Requirement: Join by code

The server SHALL expose `POST /api/rooms/{code}/join` accepting `{"name": <string 1–20 chars>}`. It SHALL append a new human seat and broadcast the updated lobby to all connected sockets. The endpoint SHALL reject with HTTP 404 if the code is unknown, HTTP 409 if the game has already started, and HTTP 409 if the room is at capacity.

#### Scenario: Successful join

- **WHEN** a player calls `/join` on a lobby room with one open seat
- **THEN** they receive a new `pid` and the room now has one more seat

#### Scenario: Join after start rejected

- **WHEN** a player attempts to join a room whose game is already in progress
- **THEN** the server responds 409

### Requirement: Add bot (host only)

The server SHALL expose `POST /api/rooms/{code}/bot` accepting `{"host_pid": <pid>}`. The action SHALL be authorized only when `host_pid` matches `room.host_pid`. On success it SHALL pick a name from the SFW bot-name roster avoiding duplicates within the room, append a bot seat, broadcast the lobby, and return `{"ok": true, "name": <picked>}`.

#### Scenario: Non-host bot add rejected

- **WHEN** a non-host calls `/bot`
- **THEN** the server responds 403

#### Scenario: Names are unique per room

- **WHEN** the host adds bots into a room
- **THEN** no two seats in the room share the same name unless the name pool was exhausted (in which case a `Bot <4-digit>` fallback name is used)

### Requirement: Update room config (host only, pre-start)

The server SHALL expose `POST /api/rooms/{code}/config` accepting `{"host_pid": <pid>, "config": <dict>}`. It SHALL be host-only, allowed only before the game starts, and SHALL parse via `GameConfig.from_dict` (ignoring unknown keys). On success it SHALL broadcast the updated lobby.

#### Scenario: Toggle 7-on-7 off

- **WHEN** the host posts `{"config": {"seven_on_seven": false}}`
- **THEN** all connected clients receive a lobby broadcast with the updated config

#### Scenario: Config change after start rejected

- **WHEN** a host attempts to change config while `room.game` exists
- **THEN** the server responds 409

### Requirement: Start game (host only, ≥2 seats)

The server SHALL expose `POST /api/rooms/{code}/start` accepting `{"host_pid": <pid>}`. It SHALL be host-only and SHALL require at least 2 seats. On success it SHALL create a `Game` with `swap_phase=True` and the current `room.config`, auto-pick face-up cards for any bot seats, broadcast initial state, and run the bot loop.

#### Scenario: Single-seat start rejected

- **WHEN** the host calls `/start` with only one seat in the room
- **THEN** the server responds 409

#### Scenario: Already-started start rejected

- **WHEN** `room.game` already exists and the host calls `/start`
- **THEN** the server responds 409

### Requirement: Rematch (host only, post-game)

The server SHALL expose `POST /api/rooms/{code}/rematch` accepting `{"host_pid": <pid>}`. It SHALL require `room.game.game_over == True`. On success it SHALL discard the finished game, start a fresh one with the same seats and config, broadcast state, and run bots.

#### Scenario: Rematch before game-over rejected

- **WHEN** a host calls `/rematch` while the game is still in progress
- **THEN** the server responds 409 with `error == "no finished game to rematch"`

### Requirement: Abort game (host only)

The server SHALL expose `POST /api/rooms/{code}/abort` accepting `{"host_pid": <pid>}`. It SHALL set `room.game = None` and broadcast the lobby. The seats SHALL remain intact so the host can restart.

#### Scenario: Abort returns room to lobby

- **WHEN** a host calls `/abort` mid-game
- **THEN** all clients receive a `lobby` broadcast and `room.game` is None

### Requirement: Leave room (non-host)

The server SHALL expose `POST /api/rooms/{code}/leave` accepting `{"pid": <pid>}`. The host SHALL NOT be allowed to leave (must abort instead). On success the seat SHALL be removed and the room SHALL be re-broadcast.

#### Scenario: Host leave rejected

- **WHEN** the host calls `/leave`
- **THEN** the server responds 409 with `error == "host can't leave — use abort instead"`

### Requirement: WebSocket lifecycle

The server SHALL expose `WS /ws/{code}/{pid}`. On connect it SHALL attach the socket to the matching seat, send an initial `lobby` or `state` message reflecting current room status, and rebroadcast the lobby so other players see the connect state. On disconnect it SHALL detach the socket and rebroadcast.

#### Scenario: Mid-game connect receives state

- **WHEN** a player connects to `/ws/<code>/<their pid>` while `room.game` exists
- **THEN** the first message they receive is `{"type": "state", "view": …}`

### Requirement: WebSocket action protocol

The WebSocket SHALL accept JSON messages with `type` ∈ {`play`, `pickup`, `set_face_up`}. Other types SHALL elicit an `error` reply. Engine rejections (`result.ok == False`) SHALL elicit an `error` reply to the originating socket only; successful actions SHALL trigger a state broadcast to all sockets followed by `run_bots()`.

#### Scenario: Unknown message type returns error

- **WHEN** a client sends `{"type": "shuffle"}`
- **THEN** the server replies `{"type": "error", "message": "unknown type: shuffle"}`

#### Scenario: Rejected play returns error to sender only

- **WHEN** a client sends a `play` that the engine rejects
- **THEN** only the sender receives `{"type": "error", "message": <reason>}` and no state broadcast is sent

#### Scenario: Successful play broadcasts state

- **WHEN** a client sends a `play` that the engine accepts
- **THEN** every connected seat receives an updated `state` message before `run_bots` is invoked

### Requirement: Bot name pool

The server SHALL ship a SFW pool of 100 playful names mocking the player and asserting bot superiority. Names SHALL be ≤ 20 characters. `pick_bot_name(taken)` SHALL return a name not already used in the room, or fall back to `Bot <4-digit>` if all names are taken.

#### Scenario: Fallback when pool exhausted

- **WHEN** the `taken` set contains all 100 names
- **THEN** `pick_bot_name` returns a string matching `^Bot \d{4}$`

### Requirement: Room code format

Room codes SHALL be exactly 4 characters drawn from `A–Z` and `0–9`. The registry's `get(code)` SHALL be case-insensitive so users can type either case.

#### Scenario: Lookup is case-insensitive

- **WHEN** a room with code `XJ4Q` exists and `REGISTRY.get("xj4q")` is called
- **THEN** the same room is returned

### Requirement: Single-process state

The room registry SHALL live entirely in process memory; no persistent store is required. Server restart SHALL forget all rooms.

#### Scenario: Rooms cleared on restart

- **WHEN** the server process is restarted
- **THEN** all prior room codes return HTTP 404 from `/api/rooms/{code}/join`

### Requirement: End-of-round endpoint

The server SHALL expose `POST /api/rooms/{code}/end_round` accepting `{"host_pid": <pid>}`. It SHALL be host-only and SHALL require an in-progress (non-`game_over`) game. On success it SHALL synthesize a game-over result: every player not already in `finished_order` SHALL be appended in **ascending hand-size order** (smaller hand finishes earlier). The engine's `game_over` SHALL be set to `True` and a state broadcast SHALL fire so all clients show the winner panel.

#### Scenario: Host ends a live round

- **WHEN** a 3-player game is in progress and the host calls `/end_round`
- **THEN** the broadcast state has `game_over: true` and `finished_order` contains all three pids ordered by ascending hand size

#### Scenario: Non-host call rejected

- **WHEN** a non-host pid calls `/end_round`
- **THEN** the server responds 403

#### Scenario: Already finished call rejected

- **WHEN** `room.game.game_over` is already `true` and `/end_round` is called
- **THEN** the server responds 409

### Requirement: Leave with bot conversion

The server SHALL accept an optional `convert_to_bot: bool` (default `false`) field on `POST /api/rooms/{code}/leave`. When `convert_to_bot` is `true` AND `room.game` is in progress, the leaver's `Seat.is_bot` SHALL be set to `True` in place (the pid remains the same, the player's hand / face-up / face-down / finished state remain untouched), the leaver's WebSocket SHALL be closed, and the room's lobby / state SHALL be re-broadcast so other clients render the seat as a bot.

When `convert_to_bot` is `true` but no game is in progress (lobby phase), the request SHALL behave as a normal leave — the seat is removed.

The host SHALL NOT be allowed to leave under any flag (matches existing rule); the host MUST use `/abort` or `/end_round`.

#### Scenario: Non-host converts seat to bot mid-game

- **WHEN** a non-host calls `/leave` with `convert_to_bot: true` mid-game
- **THEN** the seat is still present in `room.seats` but with `is_bot = True`; the player's hand size in the engine is unchanged

#### Scenario: Bot loop runs the converted seat

- **WHEN** the converted seat's pid becomes `current_pid`
- **THEN** `run_bots()` processes it as a normal bot turn (calling `decide()` on its hand)

### Requirement: Cap policy depends on connected humans

`Room.run_bots()` SHALL cap its per-call iteration count based on whether any **connected** human seats are currently in the room. A seat counts as a connected human when `is_bot == False AND socket is not None`:

- If at least one seat is a connected human, the cap remains 30 actions per call (matches the existing safety net for "humans are waiting").
- Otherwise (bot-only room, or every human seat has dropped its socket), the cap SHALL be raised to a high value sufficient to play any honest round to completion (e.g. 1000 actions) so the room can finish.

The hard "decide returned an illegal action → force pickup" and "exception during a bot turn → force pickup" fallbacks SHALL remain in place under either policy.

#### Scenario: Connected-human room keeps the strict cap

- **WHEN** at least one seat in the room is a connected human (`is_bot == False AND socket is not None`)
- **THEN** `run_bots()` exits the loop after at most 30 actions and logs an error if the cap is hit

#### Scenario: All-disconnected room runs to natural completion

- **WHEN** no seat in the room is a connected human (every seat is either a bot or a human with `socket is None`)
- **THEN** `run_bots()` continues until `game_over` is `True` (or the 1000-action lifetime ceiling), and the loop does not log a "safety cap" error on exit

### Requirement: Orphan room cleanup

The server SHALL evict any room from the registry whose seats are all disconnected (`socket is None`) AND whose `last_activity_ts` is more than 5 minutes old (configurable via `ROOM_IDLE_TIMEOUT_SECONDS`, default 300). The eviction check SHALL run opportunistically at the end of `_handle_message` and after each room-mutating REST endpoint; no separate scheduler or background task is required.

`Room.last_activity_ts` SHALL be updated on every action (play, pickup, set_face_up, config change, bot loop iteration). On connect, `last_activity_ts` SHALL be refreshed.

#### Scenario: Idle disconnected room is evicted

- **WHEN** a room has zero connected sockets and `last_activity_ts` is older than 5 minutes
- **THEN** the next post-action tick removes the room from the registry; subsequent `/join` calls receive HTTP 404

#### Scenario: Active rooms are never evicted

- **WHEN** a room is receiving WebSocket messages
- **THEN** `last_activity_ts` is refreshed and the room remains in the registry indefinitely

#### Scenario: Bot-only room is evicted after the round ends

- **WHEN** a bot-only room finishes its round and no socket reconnects within the idle window
- **THEN** the room is evicted from the registry

### Requirement: Remove bot endpoint

The server SHALL expose `POST /api/rooms/{code}/remove_bot` accepting `{"host_pid": <pid>, "bot_pid": <pid>}`. The endpoint SHALL be host-only and SHALL be allowed **only while the room is in the lobby** (`room.game is None`). On success it SHALL remove the matching bot seat from `room.seats` and broadcast the updated lobby. The endpoint SHALL respond:

- **404** if the room code is unknown.
- **403** if `host_pid` does not match `room.host_pid`.
- **409** if `room.game is not None` (a game is in progress or finished).
- **404** if `bot_pid` does not match any seat in the room.
- **409** if the matching seat is not a bot (`seat.is_bot == False`).

#### Scenario: Host removes a bot successfully

- **WHEN** the host posts `/remove_bot` with a valid `bot_pid` for a bot seat
- **THEN** the response is 200, the seat is removed from `room.seats`, and a lobby broadcast goes out

#### Scenario: Non-host attempt rejected

- **WHEN** a non-host pid posts `/remove_bot`
- **THEN** the server responds 403

#### Scenario: Remove after game starts rejected

- **WHEN** `/remove_bot` is called while `room.game is not None`
- **THEN** the server responds 409

#### Scenario: Attempt to remove a human seat rejected

- **WHEN** `/remove_bot` is called with a `bot_pid` belonging to a human seat
- **THEN** the server responds 409

#### Scenario: Unknown bot_pid rejected

- **WHEN** `/remove_bot` is called with a `bot_pid` that does not match any seat
- **THEN** the server responds 404

### Requirement: Rename endpoint

The server SHALL expose `POST /api/rooms/{code}/rename` accepting `{"pid": <pid>, "new_name": <string 1–20 chars>}`. The endpoint SHALL allow a seated player to rename **themselves** at any time (lobby or mid-round). On success it SHALL update `seat.name` (using the **trimmed** form of `new_name`) and, if a game is in progress, also update the corresponding `Player.name` on `room.game`. After the update the server SHALL broadcast the updated lobby (when `room.game is None`) or state (when a game is in progress).

The endpoint SHALL respond:

- **404** if the room code is unknown.
- **404** if `pid` does not match any seat in the room.
- **422** if `new_name` is missing, empty, or longer than 20 characters (Pydantic validation).
- **409** if any **other** seat in the room already has a name that matches `new_name` after both are trimmed and case-folded. The 409 detail SHALL include the offending name in quotes — e.g., `"name 'Mike' is already taken in this room"`.

If `new_name.strip().casefold()` equals the caller's current `seat.name.strip().casefold()`, the endpoint SHALL return **200** without modifying state or broadcasting (rename-to-self is a no-op).

The caller's `pid` is the implicit authorization — anyone holding a pid for a seat can rename that seat. There is no host gate; the only valid rename target is the caller's own seat.

#### Scenario: Player renames themselves in the lobby

- **WHEN** a seated player posts `/rename` with their own `pid` and a valid `new_name` that doesn't collide with another seat
- **THEN** the response is 200, `seat.name` reflects the trimmed new name, and a lobby broadcast goes out

#### Scenario: Player renames themselves mid-round

- **WHEN** a seated player posts `/rename` with their own `pid` and a valid `new_name` while `room.game` is in progress
- **THEN** the response is 200, both `seat.name` and `room.game.player(pid).name` reflect the new name, and a state broadcast goes out

#### Scenario: Rename to a duplicate name is rejected

- **WHEN** `/rename` is called with a `new_name` matching another seat (case-insensitive, whitespace-trimmed)
- **THEN** the response is 409 and the detail is `"name '<existing_name>' is already taken in this room"`

#### Scenario: Rename to own current name is a no-op

- **WHEN** `/rename` is called with `new_name` that matches the caller's current seat name (case-insensitive, whitespace-trimmed)
- **THEN** the response is 200 but no state change or broadcast occurs

#### Scenario: Unknown pid rejected

- **WHEN** `/rename` is called with a `pid` that does not match any seat
- **THEN** the server responds 404

#### Scenario: Empty name rejected

- **WHEN** `/rename` is called with `new_name == ""`
- **THEN** the server responds 422

#### Scenario: Overlong name rejected

- **WHEN** `/rename` is called with a `new_name` longer than 20 characters
- **THEN** the server responds 422

### Requirement: Mobile static routes

The server SHALL expose `GET /m` returning `static/mobile.html` and `GET /m/{code}` returning the same file. The shortcut URL form `<host>/m/<code>` allows a host to share a phone-friendly join link with friends.

These routes serve a **different** static page than `GET /` and `GET /room/{code}`; the latter pair continues to return `static/index.html` (the desktop UI) **unless** the request is from a mobile user agent and has no opt-out signal, in which case the server SHALL respond with a `302` redirect to the corresponding mobile path:

- `GET /` from a mobile UA → `302 Location: /m`
- `GET /room/{code}` from a mobile UA → `302 Location: /m/{code}`

A request is considered to come from a **mobile user agent** when the `User-Agent` header contains the case-sensitive substring `Mobi` (which matches `Mobile` and `Mobi/...` reliably across iOS Safari, Chrome Android, Firefox Mobile, Samsung Internet, etc.). Tablets such as iPads — which omit `Mobi` from their UA — are NOT considered mobile and continue to get the desktop UI.

The server SHALL skip the redirect (and serve `static/index.html` directly) when **any** of the following opt-out signals are present:

- A query-string parameter `desktop=1` (e.g. `GET /?desktop=1`).
- A request cookie `princess_prefer_desktop=1`.

The `/m` and `/m/{code}` routes SHALL NOT inspect the user agent. They always serve the mobile UI regardless of UA — a user who explicitly typed the `/m` URL has made a choice.

#### Scenario: /m serves mobile.html

- **WHEN** a `GET /m` request reaches the server
- **THEN** the response body is the contents of `static/mobile.html`

#### Scenario: /m/{code} serves mobile.html

- **WHEN** a `GET /m/AB12` request reaches the server
- **THEN** the response body is the contents of `static/mobile.html` (the page reads the code from `location.pathname` at runtime)

#### Scenario: Desktop UA on / serves index.html

- **WHEN** a `GET /` request reaches the server with a desktop User-Agent (e.g. `Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/...`)
- **THEN** the response body is the contents of `static/index.html`

#### Scenario: Mobile UA on / redirects to /m

- **WHEN** a `GET /` request reaches the server with a mobile User-Agent (e.g. `Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 ...) ... Mobile/15E148 Safari/...`)
- **THEN** the response is `302 Location: /m`

#### Scenario: Mobile UA on /room/{code} redirects to /m/{code}

- **WHEN** a `GET /room/AB12` request reaches the server with a mobile User-Agent
- **THEN** the response is `302 Location: /m/AB12`

#### Scenario: ?desktop=1 overrides the redirect

- **WHEN** a `GET /?desktop=1` request reaches the server with a mobile User-Agent
- **THEN** the response body is the contents of `static/index.html` (no redirect)

#### Scenario: princess_prefer_desktop cookie overrides the redirect

- **WHEN** a `GET /` request reaches the server with a mobile User-Agent and the cookie `princess_prefer_desktop=1`
- **THEN** the response body is the contents of `static/index.html` (no redirect)

#### Scenario: /m never redirects regardless of UA

- **WHEN** a desktop browser navigates to `/m` (with no `desktop=1` and no cookie)
- **THEN** the response body is the contents of `static/mobile.html` — no redirect to `/`

#### Scenario: iPad (tablet) gets desktop UI

- **WHEN** a `GET /` request reaches the server with an iPad UA that does NOT contain `Mobi`
- **THEN** the response body is the contents of `static/index.html` — no redirect

### Requirement: Per-room unique names on join and create

The server SHALL enforce that no two seats in the same room share a name. Name comparison SHALL be **case-insensitive** and **whitespace-trimmed**.

`POST /api/rooms` (create room) SHALL trim the host's `name` before persisting it on the host's seat. No dedupe check is needed at create time because the host is always the first seat.

`POST /api/rooms/{code}/join` SHALL trim the joining player's `name` and reject the request with **409 Conflict** if any existing seat (human or bot) has a matching name. The 409 detail SHALL include the offending name in quotes — e.g., `"name 'Mike' is already taken in this room"`.

`POST /api/rooms/{code}/bot` SHALL continue to use `pick_bot_name(taken)` where `taken = {s.name for s in room.seats}` — this already covers human + bot names; no behavior change required, but the check SHALL remain in place.

#### Scenario: Duplicate human-on-human join is rejected

- **WHEN** a player attempts to `POST /join` with a name that already matches an existing human seat
- **THEN** the response is 409 with detail `"name '<existing_name>' is already taken in this room"`

#### Scenario: Case-insensitive duplicate join is rejected

- **WHEN** a player attempts to `POST /join` with `"mike"` while another seat is named `"Mike"`
- **THEN** the response is 409

#### Scenario: Whitespace-padded duplicate join is rejected

- **WHEN** a player attempts to `POST /join` with `"  Mike  "` while another seat is named `"Mike"`
- **THEN** the response is 409

#### Scenario: Joining with a bot's name is rejected

- **WHEN** the host adds a bot that happens to be named `"Galaxy Brain"`, and a human player attempts to `POST /join` with `"Galaxy Brain"`
- **THEN** the response is 409

#### Scenario: Bot pick avoids collision with existing humans

- **WHEN** the host POSTs `/bot` for a room whose host is named `"Galaxy Brain"`
- **THEN** the resulting bot seat's name is NOT `"Galaxy Brain"` (the bot-name picker already considers `{s.name for s in room.seats}`)

#### Scenario: Create-room trims the host's name

- **WHEN** the host POSTs `/api/rooms` with `name = "  Mike  "`
- **THEN** the host's seat name is `"Mike"` (trimmed)

### Requirement: Health check endpoint

The server SHALL expose `GET /healthz` as an **unauthenticated**, cheap liveness probe suitable for nginx upstream health checks and external uptime monitors. The handler SHALL NOT perform any per-room work, engine work, or I/O beyond reading three in-memory counters.

The endpoint SHALL respond `200 OK` with a JSON body of shape:

```
{
  "status": "ok",
  "uptime_seconds": <int>,
  "rooms": <int>,
  "log_buffer_size": <int>
}
```

- `uptime_seconds` SHALL be the integer seconds since the application's startup time was captured (monotonic clock).
- `rooms` SHALL be the current count of rooms in the in-memory registry.
- `log_buffer_size` SHALL be the current count of entries in the in-memory ring buffer (not the buffer capacity).

The endpoint SHALL NOT require a `host_pid`, header, or cookie. It SHALL NOT consult the user-agent (no mobile redirect applies) and SHALL NOT emit any per-request log line at INFO level (DEBUG is acceptable but optional — health probes are high-frequency).

#### Scenario: Basic probe returns 200

- **WHEN** a client issues `GET /healthz` against a running server
- **THEN** the response status is 200 and the body is JSON with `status == "ok"`

#### Scenario: Payload includes diagnostic counters

- **WHEN** a client issues `GET /healthz` against a server with two active rooms and 47 buffered log entries
- **THEN** the body contains `rooms == 2` and `log_buffer_size == 47`

#### Scenario: Uptime reflects process age

- **WHEN** `GET /healthz` is called after the server has been running for at least 1 second
- **THEN** `uptime_seconds` is a non-negative integer greater than or equal to 1

#### Scenario: No authentication required

- **WHEN** `GET /healthz` is called with no body, no auth header, and no cookies
- **THEN** the response status is 200

#### Scenario: Mobile UA does not redirect

- **WHEN** `GET /healthz` is called with a mobile User-Agent header
- **THEN** the response is the JSON payload, NOT a 302 redirect to `/m`

### Requirement: Per-IP rate limiting on room mutation endpoints

The server SHALL apply per-client-IP rate limits to four HTTP endpoints to protect the in-memory room registry from flooding and to deter scripted enumeration of the 4-character room-code namespace.

The enforced limits SHALL be:

- `POST /api/rooms` — **6 requests per minute per IP**.
- `POST /api/rooms/{code}/join` — **30 requests per minute per IP**.
- `POST /api/rooms/{code}/bot` — **20 requests per minute per IP**.
- `POST /api/rooms/{code}/rename` — **30 requests per minute per IP**.

Each endpoint's quota SHALL be tracked independently — a client exhausting `/api/rooms` SHALL still be allowed to call `/join` up to that endpoint's own quota.

When a request exceeds its endpoint's quota, the server SHALL respond with **HTTP 429** and a JSON body of the form `{"detail": "<reason including the quota>"}` so existing client error helpers can surface the message verbatim.

All other HTTP endpoints (read endpoints, `/config`, `/start`, `/abort`, `/rematch`, `/leave`, `/remove_bot`, `/end_round`, mobile static routes) and all WebSocket traffic SHALL NOT be rate-limited.

#### Scenario: Create-room flood is throttled

- **WHEN** the same client IP issues more than 6 `POST /api/rooms` requests within a 60-second window
- **THEN** at least one of the later requests in that window returns **HTTP 429** with a `detail` field describing the exceeded quota

#### Scenario: Join flood is throttled

- **WHEN** the same client IP issues more than 30 `POST /api/rooms/{code}/join` requests within a 60-second window
- **THEN** at least one of the later requests in that window returns **HTTP 429**

#### Scenario: Bot-add flood is throttled

- **WHEN** the same client IP issues more than 20 `POST /api/rooms/{code}/bot` requests within a 60-second window
- **THEN** at least one of the later requests in that window returns **HTTP 429**

#### Scenario: Rename flood is throttled

- **WHEN** the same client IP issues more than 30 `POST /api/rooms/{code}/rename` requests within a 60-second window
- **THEN** at least one of the later requests in that window returns **HTTP 429**

#### Scenario: Per-endpoint quotas are independent

- **WHEN** a client IP has exhausted its `POST /api/rooms` quota for the current window
- **THEN** the same IP can still call `POST /api/rooms/{code}/join` up to that endpoint's own 30/minute quota

#### Scenario: Read endpoints are not rate-limited

- **WHEN** a client IP issues 1000 read requests in a minute (e.g. polling a public read endpoint or the mobile static page)
- **THEN** no request is rejected with HTTP 429 by the limiter

#### Scenario: WebSocket traffic is not rate-limited

- **WHEN** a connected client sends a high volume of WebSocket messages
- **THEN** no message is rejected with HTTP 429 by the limiter (engine-level rejections still apply)

### Requirement: Real client IP behind nginx

The rate-limiter's per-client key SHALL be the **original client IP** as recorded in the `X-Forwarded-For` request header set by the nginx reverse proxy. When the header contains a comma-separated list, the first entry SHALL be used as the client IP. When the header is absent, the server SHALL fall back to `request.client.host`.

#### Scenario: First XFF entry is used as the key

- **WHEN** a request arrives with `X-Forwarded-For: 203.0.113.7, 10.0.0.1`
- **THEN** the rate-limiter treats `203.0.113.7` as the client identity

#### Scenario: Fallback to direct peer when XFF missing

- **WHEN** a request arrives with no `X-Forwarded-For` header (e.g. direct local call in dev)
- **THEN** the rate-limiter uses `request.client.host` as the client identity

#### Scenario: Two distinct client IPs share independent buckets

- **WHEN** IP `A` exhausts its `POST /api/rooms` quota and IP `B` then issues a `POST /api/rooms` request
- **THEN** IP `B`'s request is served normally (its own bucket is empty)

### Requirement: Rate limiting can be disabled for dev and tests

The server SHALL honor the environment variable `PRINCESS_RATE_LIMIT_DISABLED`. When the variable is set to `1` at process startup, the limiter SHALL be disabled and no request SHALL be rejected with HTTP 429 by the limiter, regardless of volume.

The default test suite SHALL set `PRINCESS_RATE_LIMIT_DISABLED=1` before importing the server module, so existing tests are not affected by the new limits. A dedicated test SHALL clear the variable (or build a fresh app instance with the variable cleared) to verify enforcement.

#### Scenario: Env var disables enforcement

- **WHEN** the server starts with `PRINCESS_RATE_LIMIT_DISABLED=1` and the same client IP issues 100 `POST /api/rooms` requests in one minute
- **THEN** zero requests are rejected with HTTP 429 by the limiter

#### Scenario: Default (env var unset) enforces limits

- **WHEN** the server starts with `PRINCESS_RATE_LIMIT_DISABLED` unset (or set to any value other than `1`) and the same client IP exceeds an endpoint's quota
- **THEN** the over-quota requests are rejected with HTTP 429

### Requirement: WebSocket close code for permanent rejection

The WebSocket handler `WS /ws/{code}/{pid}` SHALL close the socket with **application-specific close code 4001** when the rejection is **permanent** — i.e., the URL's `code` or `pid` does not match a seated human in the current registry. The close SHALL be paired with a machine-readable `reason` string so the client can distinguish the two permanent-rejection paths:

- When the room `code` is unknown (`REGISTRY.get(code) is None`), the server SHALL close with `code=4001, reason="unknown_room"`.
- When the room is found but `pid` does not match any seat in that room (`room.seat_by_pid(pid) is None`), or the matching seat is a bot (`seat.is_bot is True`), the server SHALL close with `code=4001, reason="unknown_pid"`.

In both cases the server SHALL first send the existing JSON error message (`{"type": "error", "message": "room not found"}` or `{"type": "error", "message": "seat not found"}`) for log and human-eyeball debugging, THEN call `close(code=4001, reason=...)`.

Close codes for **transient** disconnects (network drop, normal disconnect, server crash) SHALL NOT use 4001. They continue to use the default codes (1000 for clean close, 1006 for abnormal closure) so the client can distinguish "this sentinel is dead — clear it" from "the connection blipped — retry."

#### Scenario: Unknown room code closes with 4001 unknown_room

- **WHEN** a client opens `WS /ws/ZZZZ/<any pid>` and no room with code `ZZZZ` exists
- **THEN** the server sends `{"type": "error", "message": "room not found"}` and then closes the socket with `code=4001` and `reason="unknown_room"`

#### Scenario: Unknown pid in an existing room closes with 4001 unknown_pid

- **WHEN** a client opens `WS /ws/AB12/<bogus_pid>` where `AB12` exists but no seat has that pid
- **THEN** the server sends `{"type": "error", "message": "seat not found"}` and then closes the socket with `code=4001` and `reason="unknown_pid"`

#### Scenario: Bot pid is treated as unknown_pid

- **WHEN** a client opens `WS /ws/AB12/<bot_pid>` where `AB12` exists and the matching seat is a bot
- **THEN** the server closes the socket with `code=4001` and `reason="unknown_pid"`

#### Scenario: Normal disconnect does NOT use 4001

- **WHEN** a successfully-seated client cleanly closes their socket
- **THEN** the server's close frame uses a default WebSocket close code (1000-range), NOT 4001

### Requirement: Session scoreboard

`Room` SHALL maintain a session-level scoreboard tracking per-seat counters that persist across rematches within the same room lifetime. The scoreboard SHALL be exposed at `Room.scoreboard: dict[str, dict[str, int]]` keyed by `Seat.pid`. Each entry SHALL contain at least three integer counters:

- `princess_wins` — number of rounds in this session in which the seat finished first (i.e., was `finished_order[0]` at game-over).
- `last_places` — number of rounds in which the seat finished last (i.e., was `finished_order[-1]`).
- `rounds_played` — number of rounds in which the seat appeared in `finished_order` at game-over.

A fresh entry with all three counters at `0` SHALL be created whenever a new seat is added to the room — via room creation, `/api/rooms/{code}/join`, `/api/rooms/{code}/bot`, or a `convert_to_bot` flag on `/api/rooms/{code}/leave` (the convert path keeps the existing entry untouched because the pid is unchanged).

A seat's entry SHALL be dropped when the seat is removed via `/api/rooms/{code}/remove_bot` or via `/api/rooms/{code}/leave` without `convert_to_bot`.

The room SHALL bump the scoreboard exactly once per round when `room.game.game_over` flips to `True`. The bump SHALL apply the following updates:

- `scoreboard[finished_order[0]]["princess_wins"] += 1`
- `scoreboard[finished_order[-1]]["last_places"] += 1`
- For every pid in `finished_order`, `scoreboard[pid]["rounds_played"] += 1`

The bump SHALL be idempotent — a state re-broadcast for the same already-finished `Game` SHALL NOT bump again. The implementation SHALL track which round (or whether the current `Game` instance) has already been counted so that a reconnect-driven re-broadcast, a host-only `/end_round` re-render, or any other repeat does not double-count. The "already counted" marker SHALL clear on the next `start_game` / rematch so the new round can be counted when it ends.

`/api/rooms/{code}/abort` SHALL reset every entry in the scoreboard to `{princess_wins: 0, last_places: 0, rounds_played: 0}`. Entries themselves SHALL NOT be dropped (the seats remain after abort). `/api/rooms/{code}/rematch` SHALL leave the scoreboard untouched.

When the room is evicted by the idle-room sweep, the scoreboard is dropped along with the rest of the room state (no special handling required).

#### Scenario: Fresh entry on seat creation

- **WHEN** a `Room` is created via `POST /api/rooms`
- **THEN** `room.scoreboard[host_pid] == {"princess_wins": 0, "last_places": 0, "rounds_played": 0}`

#### Scenario: Join adds an entry

- **WHEN** a player joins via `POST /api/rooms/{code}/join` and receives `pid = "p2"`
- **THEN** `room.scoreboard["p2"] == {"princess_wins": 0, "last_places": 0, "rounds_played": 0}`

#### Scenario: Add-bot adds an entry

- **WHEN** the host POSTs `/api/rooms/{code}/bot` and a new bot seat is created
- **THEN** the bot's pid exists as a fresh-zero key in `room.scoreboard`

#### Scenario: Remove-bot drops the entry

- **WHEN** the host POSTs `/api/rooms/{code}/remove_bot` with a valid bot pid
- **THEN** that pid is absent from `room.scoreboard` after the call

#### Scenario: Leave (without convert_to_bot) drops the entry

- **WHEN** a non-host POSTs `/api/rooms/{code}/leave` with `convert_to_bot: false`
- **THEN** that pid is absent from `room.scoreboard` after the call

#### Scenario: Leave with convert_to_bot preserves the entry

- **WHEN** a non-host POSTs `/api/rooms/{code}/leave` with `convert_to_bot: true` mid-game
- **THEN** that pid's `room.scoreboard` entry is unchanged (the seat stays under the same pid as a bot)

#### Scenario: Game-over bumps the winner and the last-place seat

- **WHEN** a 3-player round ends with `finished_order == ["p1", "p0", "p2"]` and broadcast_state fires
- **THEN** `room.scoreboard["p1"]["princess_wins"]` is incremented by 1, `room.scoreboard["p2"]["last_places"]` is incremented by 1, and each of `p0`, `p1`, `p2` sees `rounds_played` increase by 1

#### Scenario: Re-broadcast of a finished game does not double-count

- **WHEN** a round ends, broadcast_state fires once, then a player reconnects and broadcast_state fires a second time for the same finished `Game`
- **THEN** every counter that was bumped on the first broadcast remains at the same value after the second broadcast (no double count)

#### Scenario: Rematch preserves counters

- **WHEN** a round ends, the scoreboard bumps, and the host POSTs `/api/rooms/{code}/rematch`
- **THEN** the scoreboard counters retain their previous values after the new game starts, and a subsequent game-over for the new round bumps from those values (not from zero)

#### Scenario: Abort zeroes the scoreboard

- **WHEN** the host POSTs `/api/rooms/{code}/abort` while scoreboard entries are non-zero
- **THEN** every entry in `room.scoreboard` is reset to `{"princess_wins": 0, "last_places": 0, "rounds_played": 0}` and no entry is dropped (the seats persist)

#### Scenario: 2-player round bumps both Princess and last place on different pids

- **WHEN** a 2-player round ends with `finished_order == ["p0", "p1"]`
- **THEN** `room.scoreboard["p0"]["princess_wins"] += 1` and `room.scoreboard["p1"]["last_places"] += 1` — both fire from the same single round

### Requirement: Scoreboard in lobby and state broadcasts

`Room.public_lobby()` SHALL include a `"scoreboard"` field at the top level — a dict mapping each seated pid to its scoreboard entry (`{princess_wins, last_places, rounds_played}`). The set of keys SHALL match the set of pids in `room.seats`.

The WebSocket `{"type": "state", ...}` message produced for each seated, connected player SHALL include the room's scoreboard at the top level of the envelope, alongside the existing `view` field — `{"type": "state", "view": <view_for_pid>, "scoreboard": {pid: {...}, ...}}`. The engine's `view_for(pid)` SHALL NOT be modified.

The scoreboard broadcast SHALL fire on every existing broadcast trigger — connect, lobby change, config change, action, game-over — so clients reflect the latest counters without a separate request.

#### Scenario: Lobby broadcast includes scoreboard

- **WHEN** a client receives a `{"type": "lobby", "room": ...}` message
- **THEN** the `room` object contains a `"scoreboard"` key whose value is a dict with one entry per seated pid, and each entry contains `princess_wins`, `last_places`, `rounds_played` as integers

#### Scenario: State broadcast includes scoreboard

- **WHEN** a seated player's WebSocket receives a `{"type": "state", ...}` message
- **THEN** the message contains a top-level `"scoreboard"` key whose value mirrors `room.scoreboard` at the moment of the broadcast

#### Scenario: Scoreboard reflects the latest bump

- **WHEN** a round ends and the broadcast state is delivered
- **THEN** the `"scoreboard"` field in the broadcast already reflects the post-bump counters (the winner shows `princess_wins` one higher than before the round)
