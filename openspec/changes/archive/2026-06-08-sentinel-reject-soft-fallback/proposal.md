## Why

The `deep-link-auto-join` change shipped a three-tier chain: session sentinel → saved name → focused name view. Tier 1 — the session sentinel — opens a WS with the stored pid and, if the server doesn't recognize that pid (the room was evicted, the seat was removed, a new server started), the close arrives before the first message. The current fallback is `location.reload()`: a brutal full-page refresh that flashes the URL, drops all in-memory state, and re-runs the auto-join chain from scratch.

That works, but it feels broken. The user sees the URL bar flicker and a white flash; meanwhile we already know exactly what to do — clear the dead sentinel, run tier 2 (saved name) or tier 3 (focused name view) in the same page.

There's also a deeper ambiguity. The server today closes the socket with FastAPI's default code (1000, with no semantic) in both **permanent** rejection (the pid is unknown — try a fresh join) and **transient** drop (network blip — retry the same pid). The client can't tell them apart, so it has to assume the worst and always reload. A clean close code from the server makes the rejection unambiguous.

## What Changes

- **Server (`princess/server.py`):** The WebSocket handler SHALL close with **WebSocket close code 4001** and reason `"unknown_pid"` when the room is found but the seat for `pid` doesn't exist (or is a bot seat). The existing `"room not found"` close (no matching code) SHALL also use **4001** with reason `"unknown_room"` to give the client a single, unambiguous "this sentinel is dead" signal. Other close paths (normal disconnect, server crash, network drop) continue to use the default codes — they mean "transient; retry later" and are owned by the planned `websocket-reconnect` change, not this one.
- **Desktop frontend (`static/app.js`):** On WS close, if `event.code === 4001`, the client SHALL clear `sessionStorage.princess_session`, reset the partially-seated DOM (hide `#room-view`, show `#lobby`), and call `autoJoinFromUrl()` again — which runs tier 2 (saved name) or tier 3 (focused view) **in the same page**, with no `location.reload()`. For any other close code, the existing behavior (today: nothing / a future `websocket-reconnect` change) applies; this change scopes itself strictly to the permanent-rejection signal.
- **Mobile frontend (`static/mobile.js`):** Same in-page retry on `event.code === 4001`. Hides `#m-room` / `#m-game`, shows `#m-landing`, clears the sentinel, calls `autoJoinFromUrl()` again. No reload.
- **DOM reset helper:** Both clients SHALL expose a small `resetSeatedUi()` (or equivalent) that hides the seated-view containers (`#room-view`, `#game-view` on desktop; `#m-room`, `#m-game` on mobile) and shows the landing container (`#lobby` / `#m-landing`) so the second-tier focused view (or saved-name auto-join) starts from a clean slate.

## Capabilities

### Modified Capabilities

- `room-server`: WebSocket handler closes with code 4001 (`unknown_room` / `unknown_pid`) on permanent rejection, enabling clients to distinguish a dead sentinel from a transient drop.
- `web-frontend`: deep-link auto-join replaces the `location.reload()` fallback with an in-page tier 2 / tier 3 retry on 4001.
- `mobile-frontend`: same, mirrored for the mobile UI.

### New Capabilities

(none)

## Impact

- **Affected code:**
  - `princess/server.py` — change the two pre-handshake close paths in `gameplay_socket()` to use `WebSocket.close(code=4001, reason="unknown_room" | "unknown_pid")`. No other server logic changes.
  - `static/app.js` — wire `ws.onclose` to inspect `event.code`. On `4001`, clear `sessionStorage.princess_session`, call `resetSeatedUi()`, then call `autoJoinFromUrl()` to retry. Remove the existing `location.reload()` from the tier-1 failure path.
  - `static/mobile.js` — same wiring, mobile element ids.
- **Affected APIs:** the WebSocket close code surface changes from "default 1000 / 1006" to **4001** for permanent pid/room rejection. This is a private contract between the server and the bundled clients; no external consumer relies on the prior code.
- **Affected dependencies:** none.
- **Docs touched:** `CHANGELOG.md` `### Changed` (the reload → in-page retry). No README change — this is internal mechanics.
- **Coordination with `websocket-reconnect` (separate change):** that change owns transient-drop reconnect-with-backoff (`event.code !== 4001`). This change owns the permanent-rejection clean fallback (`event.code === 4001`). They are complementary and independent — either can ship first.
- **Out of scope:**
  - Reconnect-with-backoff on transient drops (covered by `websocket-reconnect`).
  - Any server-side change beyond the close code (no new endpoints, no new validation).
  - Reusing the close-code mechanism for other rejection reasons (room full, name taken, etc.) — those go through REST and never reach the WS handshake.
  - Persisting `princess_session` longer than the tab (still `sessionStorage`).
