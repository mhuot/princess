## Why

Princess is a phone-first game. Phones flake — a tunnel, an elevator, a Wi-Fi-to-cellular handoff, a few seconds of bad signal mid-round. Today when that happens the WebSocket dies, the user sees "**Disconnected. Refresh to reconnect.**" pinned in the waiting slot, and the seat just sits there frozen until they remember to swipe down and reload. The seat is still on the server — the server's `Room.connect_socket(pid, socket)` happily accepts a returning seat's pid right up until idle eviction — but the user has to manually do the rejoin dance.

That's a bad outcome for a hiccup that the client could absorb invisibly. Reconnect should "just work."

## What Changes

- **Auto-reconnect with exponential backoff:** when an already-established WebSocket closes mid-session, the frontend SHALL reopen it automatically with the SAME `pid` against the SAME `/ws/<code>/<pid>` URL. Backoff: 1s, 2s, 4s, 8s, 16s, 16s, 16s, …, capping at 16s between attempts.
- **Give-up threshold:** after **10 consecutive failed attempts** OR **90 seconds elapsed since the first close event** (whichever comes first), the frontend SHALL stop trying and surface a terminal "**Disconnected — refresh to reconnect.**" banner.
- **Visible status banner:** a small fixed-position chip at the top of the viewport (above all other content, below any system status bar) SHALL show the connection state during reconnect attempts. Three labels:
  - "**Reconnecting…**" — visible while a reconnect attempt is pending or in-flight.
  - "**Reconnected**" — flashed briefly (~1500 ms) on the first successful message after a reconnect, then auto-hidden.
  - "**Disconnected — refresh to reconnect.**" — terminal state after the give-up threshold.
- **Pause game actions during reconnect:** while the banner shows "Reconnecting…" the Play and Pick-up buttons (desktop: `#play-btn`, `#pickup-btn`; mobile: `#m-play-btn`, `#m-pickup-btn`) SHALL be `disabled`. On successful reconnect they re-enable on the first received `state` or `lobby` broadcast (the server's resync after reopen).
- **Tier-1 sentinel guard still wins:** the existing `_wsGotMessage` flag from `deep-link-auto-join` already distinguishes "never connected" (sentinel pid is stale → clear it and `location.reload()`) from "connected then dropped" (genuine hiccup). Auto-reconnect SHALL only apply to the **connected-then-dropped** case. The "never connected" path is unchanged.
- **No server changes.** The server already accepts the returning pid via `Room.connect_socket(pid, socket)`. Reconnect re-uses the existing handshake.
- **Affects both UIs.** Desktop (`/`, `static/app.js` + `static/index.html` + `static/styles.css`) and mobile (`/m`, `static/mobile.js` + `static/mobile.html` + `static/mobile.css`).

## Capabilities

### Modified Capabilities

- `web-frontend`: a previously-connected WebSocket close triggers exponential-backoff auto-reconnect with a visible banner.
- `mobile-frontend`: same behavior, parallel scenarios, mobile-styled banner.

### New Capabilities

(none)

## Impact

- **Affected code:**
  - `static/app.js` — refactor `openSocket()` to track attempt count + start-of-disconnect timestamp; on `close` (after a prior message had arrived) schedule a reopen via a backoff helper; update the existing close handler to call the new flow instead of pinning the disconnect label. Add a tiny banner-state helper (`setConnState("reconnecting" | "reconnected" | "lost" | "live")`). Wire the action-row disable/enable into this helper.
  - `static/index.html` — add a single `<div id="conn-banner" role="status" aria-live="polite" hidden></div>` at the top of `<body>` (before `#lobby`).
  - `static/styles.css` — add fixed-position banner styling (top center, accent background, drop shadow, respects `prefers-reduced-motion` for any fade).
  - `static/mobile.js` — mirror the desktop changes against the mobile `openSocket()`.
  - `static/mobile.html` — add `<div id="m-conn-banner" role="status" aria-live="polite" hidden></div>` at the top of the body.
  - `static/mobile.css` — mobile banner styling (top, safe-area-aware, ≥ 44 px tall if interactive — but it's not interactive, so smaller is fine).
- **Affected APIs:** none. The WebSocket endpoint `/ws/<code>/<pid>` already accepts returning seats.
- **Affected dependencies:** none.
- **Docs touched:** `CHANGELOG.md` `### Added`. `README.md` gets a one-sentence mention in the "phones flake" section if one exists, otherwise just the changelog.
- **Out of scope:**
  - Server-side push-on-evict so the client learns *why* the seat was lost. Today a "lost forever" seat (room evicted) surfaces as the same close → tier-1 reload path that already exists.
  - REST-side heartbeat or session resume — purely WS-level.
  - A user-facing "Reconnect now" button on the terminal "Disconnected" banner. The user can refresh; the banner already tells them so. We can revisit if anyone asks.
  - Offline action queueing. While reconnecting, the Play/Pick-up buttons are simply disabled. No actions queue up to fire on reconnect.
  - Reconnect across page navigations (closing the tab still drops the seat — that's the existing sessionStorage lifetime).
  - Tracking reconnect telemetry in logs (the server-side WS open/close logs already cover this for ops).
