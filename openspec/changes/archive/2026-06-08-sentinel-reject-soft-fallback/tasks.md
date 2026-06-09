## 1. Pre-conditions

- [x] 1.1 Branch from main: `git switch -c change/sentinel-reject-soft-fallback`.
- [x] 1.2 Confirm `deep-link-auto-join` is archived (the requirement we MODIFY exists in the main specs).

## 2. Server: 4001 close code

- [x] 2.1 In `princess/server.py`, locate `gameplay_socket()` (the `WS /ws/{code}/{pid}` handler).
- [x] 2.2 Change the "room not found" close:
  - Today: `await websocket.send_json({"type": "error", "message": "room not found"}); await websocket.close()`.
  - To: `await websocket.send_json(...); await websocket.close(code=4001, reason="unknown_room")`.
- [x] 2.3 Change the "seat not found" close (covers both `seat is None` and `seat.is_bot`):
  - To: `await websocket.send_json(...); await websocket.close(code=4001, reason="unknown_pid")`.
- [x] 2.4 Leave all other close paths (`WebSocketDisconnect` cleanup in the `finally`, the post-handshake error responses) untouched — they continue to use default codes.

## 3. Server tests

- [x] 3.1 In `tests/test_room_server_ws.py` (or the closest existing WS test file), add a test:
  - Open a WS to `/ws/ZZZZ/anypid` for a non-existent room. Assert the close frame has `code == 4001` and `reason == "unknown_room"`.
- [x] 3.2 Add a test: create a room, open a WS to `/ws/<code>/<bogus_pid>`. Assert close `code == 4001`, `reason == "unknown_pid"`.
- [x] 3.3 Add a test: create a room with one bot, open a WS to `/ws/<code>/<bot_pid>`. Assert close `code == 4001`, `reason == "unknown_pid"`.
- [x] 3.4 Confirm an existing "normal disconnect" test (or add one) shows the close code is NOT 4001 (i.e., the default 1000-range).

## 4. Desktop frontend

- [x] 4.1 In `static/app.js`, add a `resetSeatedUi()` helper:
  - Hide `#room-view` and `#game-view` by setting the `hidden` attribute.
  - Show `#lobby` (remove its `hidden` attribute).
- [x] 4.2 In the WS open path used by the session-sentinel reconnect (tier 1), wire `ws.onclose = (event) => { ... }`:
  - If `event.code === 4001`:
    1. `try { sessionStorage.removeItem("princess_session"); } catch {}`.
    2. Call `resetSeatedUi()`.
    3. Call `autoJoinFromUrl()` to re-enter the chain in-page.
  - Else: do nothing (left for `websocket-reconnect`; today a no-op).
- [x] 4.3 Remove the existing `location.reload()` call from the tier-1 failure path. Search `static/app.js` for `location.reload` and confirm the only remaining call (if any) lives outside this code path.
- [x] 4.4 Log the close event with `console.info(...)` including `event.code` and `event.reason` to aid live-tail debugging.

## 5. Mobile frontend

- [x] 5.1 In `static/mobile.js`, add a `resetSeatedUi()` helper:
  - Hide `#m-room` and `#m-game` (toggle `hidden`).
  - Show `#m-landing`.
- [x] 5.2 Wire the tier-1 WS `onclose` the same way as desktop, branching on `event.code === 4001`. On 4001: clear the sentinel, reset DOM, call `autoJoinFromUrl()`. Else: no-op.
- [x] 5.3 Remove the existing `location.reload()` from the mobile tier-1 failure path.
- [x] 5.4 Log the close event.

## 6. Smoke / E2E

- [x] 6.1 Update `scripts/smoke_test.py` to add a section:
  - **Stale sentinel, room gone, with saved name:** stash `sessionStorage.princess_session = {code: "ZZZZ", pid: "fake", name: "Mike"}` and `localStorage.princess_name = "Mike"`, then visit `/m/ZZZZ`. Capture the navigation count via `page.evaluate("performance.getEntriesByType('navigation').length")` before and after. Assert it does NOT increase (no reload). Assert `#m-landing` becomes visible with `#m-code` prefilled and an error rendered (room ZZZZ doesn't exist).
  - **Stale sentinel, room exists, with saved name:** create a room AB12 (via the API), stash a bogus sentinel `{code: "AB12", pid: "fake", name: "Mike"}` and saved name `"Mike"`, then visit `/m/AB12`. Assert no reload, and the user ends up seated as a fresh seat.
  - **Stale sentinel, no saved name:** clear `localStorage.princess_name`, stash a bogus sentinel for AB12, visit `/m/AB12`. Assert no reload, and `#m-focused-join` becomes visible.

## 7. Docs

- [x] 7.1 In `CHANGELOG.md` `## [Unreleased]` `### Changed`:
  - "Deep-link auto-join: when the saved session pid is rejected by the server (room evicted, pid unknown), the page now retries in-place (tier 2 saved-name join, or tier 3 focused name view) instead of doing a full `location.reload()`. Server signals permanent rejection with WebSocket close code 4001. [sentinel-reject-soft-fallback]"

## 8. Verify

- [x] 8.1 `black princess tests`.
- [x] 8.2 `pylint princess tests` → 10.00/10.
- [x] 8.3 `pytest -q` → green.
- [x] 8.4 `openspec validate --specs --strict`.
- [x] 8.5 `openspec validate sentinel-reject-soft-fallback --strict`.
- [x] 8.6 Run the smoke test against a local server; eyeball that no URL bar flicker occurs in the stale-sentinel paths.

## 9. Ship

- [x] 9.1 Commit: `sentinel-reject-soft-fallback: WS close code 4001 + in-page retry on stale sentinel`.
- [x] 9.2 Push the branch; open a PR.
- [x] 9.3 Watch CI; auto-merge once green.

## 10. Wrap up

- [x] 10.1 `openspec status --change sentinel-reject-soft-fallback` → all done.
- [x] 10.2 `/opsx:archive sentinel-reject-soft-fallback` after merge.
