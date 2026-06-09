## Context

The `deep-link-auto-join` change introduced a three-tier auto-join chain on deep-link landing. Tier 1 — the session sentinel — opens a WebSocket with the saved pid. If that pid is stale (server restart wiped the room, the seat was evicted for idleness, the room was deleted), the WebSocket closes immediately after the server's pre-handshake "seat not found" error. The current fallback is `location.reload()`, which re-runs the chain from scratch via a full page refresh.

Two problems:

1. **UX.** A reload is loud — URL bar flicker, white flash, lost in-memory state. We already know exactly which tier to run next; we shouldn't blow the page away to get there.
2. **Ambiguity.** The server's pre-handshake close (`websocket.close()` after sending an error message) lands with the default code. A genuine transient drop (server crashed mid-game, network blip) lands with code 1006. The client today can't distinguish "your pid is dead" from "your pid is fine, the connection blipped" — so it reloads in both cases, which is fine for the dead-pid case and wasteful (or wrong) for the blip case. The planned `websocket-reconnect` change wants to reconnect transient drops with backoff; this only works if "permanent rejection" has a distinct, machine-readable signal.

This change solves both: server emits a clear close code (4001) on permanent rejection, client handles 4001 by clearing the sentinel and re-running tier 2 / tier 3 in-page.

## Goals / Non-Goals

**Goals:**
- The user never sees a `location.reload()` flash when their sentinel is rejected.
- Server signals permanent rejection unambiguously (code 4001) so the client can branch cleanly.
- Same UX semantics on desktop and mobile.
- The change is independent of `websocket-reconnect` — either can ship first without conflict.

**Non-Goals:**
- Reconnect-with-backoff on transient drops (different close codes; different change).
- New REST endpoints or session-validation surface (the WS handshake remains the validator).
- Persisting `princess_session` beyond the tab.
- Exposing 4001 as a public API (it's a private server↔bundled-client contract; future external clients would learn it from the protocol doc, not negotiate it).

## Decisions

### Close code 4001 for permanent rejection
**Choice:** Server closes with `code=4001` and `reason="unknown_pid"` (or `"unknown_room"`) in `gameplay_socket()` for the two pre-handshake rejection paths.
**Why:** WebSocket close codes in the 4000–4999 range are reserved for application-specific use (per RFC 6455). 4001 is widely used as the first app code; the reason string is machine-readable for the client and human-readable in server logs. The default close code (1000) and the abnormal-closure code (1006) both leave the client guessing.

### Two reasons, one code
**Choice:** Both "room not found" and "seat not found" use 4001 with different reason strings (`"unknown_room"` vs `"unknown_pid"`).
**Why:** From the client's perspective the recovery is identical — "this sentinel is dead, clear it and run tier 2." Splitting into two codes (e.g., 4001 vs 4002) buys nothing and adds a switch the client doesn't need. The reason string is there for log-grepping when debugging.

### Client branches on `event.code === 4001` only
**Choice:** The client's `onclose` handler checks `event.code === 4001` to trigger the sentinel-clear + tier 2/3 retry. Other codes fall through to whatever exists (today: nothing; tomorrow: `websocket-reconnect`'s backoff logic).
**Why:** Strict scoping. This change owns the permanent-rejection path; the transient-retry path is a separate change. A simple `if (event.code === 4001) { ... } else { /* leave for websocket-reconnect */ }` keeps the boundary clean.

### Reset the seated UI before re-running the chain
**Choice:** Before calling `autoJoinFromUrl()` for the in-page retry, the client hides the partially-loaded seated containers (`#room-view`, `#game-view` on desktop; `#m-room`, `#m-game` on mobile) and shows the landing container (`#lobby` / `#m-landing`).
**Why:** Tier 1 may have already toggled DOM into "seated" before the WS handshake failed. Tier 2 or tier 3 needs a clean landing-page DOM to operate against, or we'd end up with a focused-name view layered over a partially-rendered room.

### No reload anywhere in this chain
**Choice:** Remove the existing `location.reload()` from the tier-1 failure path entirely. The retry runs in the same page.
**Why:** The whole point of the change. If the in-page retry itself fails (network down, etc.), the tier 2 / tier 3 logic already has its own error UX (focused-view error slot, fallback to standard lobby). No reason to add a reload as a third-level safety net — it would just resurrect the original bad UX.

### Pre-handshake close, not post-handshake reject
**Choice:** The server still closes the socket synchronously after sending the error message; we're not adding a post-accept "reject" message protocol.
**Why:** The current handler already accepts → sends error → closes. We just change `close()` (default args) to `close(code=4001, reason="...")`. Minimal server delta; no protocol redesign.

### Sentinel-clear is part of the 4001 handler
**Choice:** When the client sees 4001 it deletes `sessionStorage.princess_session` before re-running the chain.
**Why:** Otherwise tier 1 would fire again, re-rejecting, ad infinitum. The 4001 signal is itself the "this sentinel is bad" verdict; the client trusts it and discards.

### Storage write is best-effort (unchanged)
**Choice:** Inherits the existing wrapping in `try { ... } catch {}`. A failed `removeItem` doesn't break the retry.
**Why:** Consistency with how the existing change handles storage; private browsing and quota errors are nuisances, not blockers.

## Risks / Trade-offs

| Risk | Mitigation |
| --- | --- |
| A future server change emits 4001 for a different reason and the client mis-handles it | The reason string is the disambiguator. Client logs the close event with both code and reason. Server keeps the two 4001 paths fully covered by tests. |
| Old bundled clients (cached in a browser) don't recognize 4001 and ignore it | The old client did `location.reload()` on *any* WS close before the first message — which gets the user back to the same fallback behavior. Slightly worse UX for one cache cycle; correct outcome. |
| The retry loops if tier 2 / tier 3 also hits 4001 (e.g., transient server bug) | Tier 2 (saved-name join) doesn't go through the WS until *after* a successful REST `/join` which returns a fresh pid. A fresh pid can't be 4001-rejected unless the room is also gone — in which case the REST `/join` itself returns 404, and the existing failure path (hide focused view, show standard lobby with error) takes over. No infinite WS loop. |
| Browser implementations of `event.code` for app-defined codes vary | All current browsers (Chrome, Safari, Firefox) correctly surface 4001 from a server `close(code=4001)` call. RFC-compliant. |
| Reason string isn't observable on the client in some browsers | `event.reason` is widely available in modern browsers. Even if a browser flunked it, the `code` alone is sufficient — `reason` is for logging. |

## Migration Plan

1. **`princess/server.py`:**
   - In `gameplay_socket()`, change the two pre-handshake `await websocket.close()` calls to `await websocket.close(code=4001, reason="unknown_room")` and `await websocket.close(code=4001, reason="unknown_pid")` respectively.
   - No other server logic changes; the error message JSON is sent first, as today.
2. **`static/app.js`:**
   - Find the existing `ws.onclose` handler in the auto-join path (the one that today does `location.reload()` for tier-1 failure).
   - Replace with a branch on `event.code`:
     - `=== 4001`: try-catch `sessionStorage.removeItem("princess_session")`, call `resetSeatedUi()`, call `autoJoinFromUrl()`.
     - else: leave for `websocket-reconnect` to handle (today, no-op).
   - Add `resetSeatedUi()`: hide `#room-view` and `#game-view` (via `hidden`), show `#lobby`.
3. **`static/mobile.js`:** same wiring with mobile element ids (`#m-room`, `#m-game`, `#m-landing`).
4. **Tests:**
   - Add a unit test for `gameplay_socket()` confirming the close-code/reason on both rejection paths.
   - Update `scripts/smoke_test.py` to exercise the in-page retry: stash a bogus sentinel (`code: "ZZZZ", pid: "fake"`) for a non-existent room, visit `/m/<code>` where the code exists but no sentinel matches, verify the page does NOT reload (no `navigation` event after the initial load) and the focused view appears.
5. **CHANGELOG, no README change.** Internal mechanics.
6. Commit + push + CI + merge.

Rollback: revert the four files (server + two static + one test).

## Open Questions

- Should we also reuse 4001 for the post-handshake "your seat was evicted while you were connected" case? **Recommendation:** out of scope. That path is the `orphan-cleanup` regime and is a different recovery (the user was already seated; we should explain, not silently retry). Track in a separate change if needed.
- Should `event.reason` be surfaced to the user (e.g., "Your session expired. Rejoining…")? **Recommendation:** not in this change. The retry should be silent — the user shouldn't have to know their pid was stale. If retry fails, the tier 2 / tier 3 error UX takes over.
