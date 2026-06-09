## 1. Pre-conditions

- [x] 1.1 Branch from main: `git switch -c change/websocket-reconnect`.

## 2. Desktop frontend

- [x] 2.1 In `static/index.html`, add a connection banner as the first child of `<body>`:

  ```html
  <div id="conn-banner" role="status" aria-live="polite" hidden></div>
  ```

- [x] 2.2 In `static/app.js`:
  - Add fields to `state`: `connState: "live"`, `_reconnectAttempt: 0`, `_firstCloseTs: null`, `_reconnectTimer: null`, `_reconnectedFlashTimer: null`.
  - Add `setConnState(label)` helper:
    - Updates `state.connState`.
    - Maps to text on `#conn-banner`: `"reconnecting"` → `"Reconnecting…"`, `"reconnected"` → `"Reconnected"`, `"lost"` → `"Disconnected — refresh to reconnect."`, `"live"` → `""`.
    - Toggles a state class on the banner (`.reconnecting` / `.reconnected` / `.lost`) and the `hidden` attribute (hidden iff state is `"live"`).
    - Sets `disabled` on `#play-btn` and `#pickup-btn` for `"reconnecting"` and `"lost"`; clears `disabled` on `"reconnected"` and `"live"` (subject to normal turn rules — the next state render owns final enable/disable).
  - Add `scheduleReconnect()` helper:
    - Computes delay = `Math.min(2 ** (state._reconnectAttempt - 1), 16) * 1000`.
    - `clearTimeout(state._reconnectTimer)` defensively.
    - Calls `setConnState("reconnecting")`.
    - `state._reconnectTimer = setTimeout(openSocket, delay)`.
  - Refactor `openSocket()`:
    - On every `message` event: existing `handleMessage` call, plus — if `state.connState === "reconnecting"`:
      - call `setConnState("reconnected")`,
      - reset `state._reconnectAttempt = 0`, `state._firstCloseTs = null`,
      - clear `state._reconnectTimer`,
      - schedule `state._reconnectedFlashTimer = setTimeout(() => setConnState("live"), 1500)`.
    - On `close` event:
      - If `!state._wsGotMessage`: existing tier-1 sentinel-fail path (`clearSession()`, `location.reload()`) — UNCHANGED.
      - Else:
        - If `state._firstCloseTs === null`, set `state._firstCloseTs = Date.now()`.
        - Increment `state._reconnectAttempt`.
        - If `state._reconnectAttempt > 10` OR `Date.now() - state._firstCloseTs > 90_000`, call `setConnState("lost")` and return (no further retries).
        - Else call `scheduleReconnect()`.

- [x] 2.3 In `static/styles.css`, add a `#conn-banner` block:
  - `position: fixed; top: 0; left: 50%; transform: translateX(-50%);`
  - Accent background, white text, ≥ 7:1 contrast.
  - Drop shadow.
  - `z-index` above the lobby/game layouts.
  - State classes `.reconnecting`, `.reconnected`, `.lost` may tweak background color (e.g., neutral for reconnecting, green for reconnected, red for lost).
  - Optional fade-in via `transition: opacity 150ms`, gated behind `@media (prefers-reduced-motion: no-preference)`.

## 3. Mobile frontend

- [x] 3.1 In `static/mobile.html`, add the connection banner as the first child of `<body>`:

  ```html
  <div id="m-conn-banner" role="status" aria-live="polite" hidden></div>
  ```

- [x] 3.2 In `static/mobile.js`:
  - Add the same `connState` + reconnect fields to `state`.
  - Add a `setConnState(label)` helper targeting mobile element ids (`#m-conn-banner`, `#m-play-btn`, `#m-pickup-btn`).
  - Add `scheduleReconnect()` with identical timing semantics.
  - Refactor `openSocket()` with the same three branches (resync flash on message, tier-1 sentinel on `!_wsGotMessage`, scheduled retry / terminal `lost` on `_wsGotMessage`).

- [x] 3.3 In `static/mobile.css`, add a `#m-conn-banner` block:
  - `position: fixed; top: env(safe-area-inset-top); left: 50%; transform: translateX(-50%);`
  - Background, text, contrast (matching desktop palette).
  - Compact padding (it's not interactive, so the 44 × 44 px floor doesn't apply).
  - `z-index` above the sticky action bar and top bar.
  - State classes parallel to desktop.

## 4. Shared timer & cleanup

- [x] 4.1 Both files: when entering `"reconnected"` and again when entering `"live"`, defensively `clearTimeout` on both `_reconnectTimer` and `_reconnectedFlashTimer` to avoid stale timers firing across cycles.
- [x] 4.2 Both files: when entering `"lost"`, `clearTimeout(state._reconnectTimer)` and leave `_reconnectedFlashTimer` cleared.

## 5. Docs

- [x] 5.1 In `CHANGELOG.md` `## [Unreleased]` `### Added`:
  - "Mid-session WebSocket drops now **auto-reconnect** with exponential backoff and a small `Reconnecting…` banner — no more manual refresh when your signal hiccups. Applies to desktop and mobile. After ~90 seconds of failed attempts the banner falls back to the existing 'Disconnected — refresh to reconnect.' message. [websocket-reconnect]"

## 6. Verify

- [x] 6.1 `black princess tests`.
- [x] 6.2 `pylint princess tests` → 10.00/10.
- [x] 6.3 `pytest -q` → green (no test changes expected — this is pure frontend).
- [x] 6.4 `openspec validate --specs --strict` and `openspec validate websocket-reconnect --strict`.
- [x] 6.5 Update `scripts/smoke_test.py`:
  - **Desktop reconnect:** open a room with a bot, start a game, then use Playwright's `page.context.set_offline(True)` for ~3s. Assert `#conn-banner` becomes visible with text `Reconnecting…` and both `#play-btn` and `#pickup-btn` carry the `disabled` attribute. Then `set_offline(False)`; assert the banner flips to `Reconnected`, then hides; assert the buttons re-enable on the next state broadcast.
  - **Mobile reconnect:** same flow against `/m/<code>` with `#m-conn-banner`, `#m-play-btn`, `#m-pickup-btn`.
  - **Terminal state:** mock the WebSocket to fail open 11 consecutive times (e.g., by patching the URL via a CDP request-interception); assert the banner ends in `Disconnected — refresh to reconnect.` and no further reconnect scheduling occurs.
  - **Tier-1 sentinel still wins:** pre-seed `sessionStorage.princess_session` with a bogus pid; open `/room/AB12`; assert the page reloads (existing behavior) and the reconnect banner is NOT shown.

## 7. Ship

- [x] 7.1 Commit: `websocket-reconnect: Auto-reconnect with backoff + status banner`.
- [x] 7.2 Push the branch; open a PR.
- [x] 7.3 Watch CI; auto-merge once green.

## 8. Wrap up

- [x] 8.1 `openspec status --change websocket-reconnect` → all sections done.
- [x] 8.2 `/opsx:archive websocket-reconnect` after merge.
