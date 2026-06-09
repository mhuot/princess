## Context

`deep-link-auto-join` established the right primitives for resilient sessions: a `sessionStorage.princess_session = {code, pid, name}` sentinel that survives a refresh, and a `_wsGotMessage` flag on `state` that distinguishes "the WS opened but the server immediately closed it because the pid is stale" from "we were happily playing and the connection dropped."

The first case (`_wsGotMessage === false` at close time) is already handled: clear the sentinel and `location.reload()`, which falls through to tier-2 (saved name auto-join) or tier-3 (focused name view).

The second case (`_wsGotMessage === true` at close time) is currently a dead end — the close handler just writes "Disconnected. Refresh to reconnect." into the waiting slot and stops. **That's what this change fixes.** The pid is still valid (until the room evicts on idle), so we should just reopen the socket. Phones drop signal all the time; reconnect should be invisible.

## Goals / Non-Goals

**Goals:**
- A WebSocket drop after a successful session reconnects automatically without user action.
- The user sees a small, calm status indicator while reconnect is in progress — enough that they know something is happening, not so much that the game ride feels broken.
- Play and Pick-up are disabled during reconnect so the user doesn't fire actions into a dead socket.
- After ~90 seconds of failed attempts, fall back to the existing "refresh to reconnect" terminal state instead of looping forever.
- Symmetric behavior on desktop and mobile.

**Non-Goals:**
- Server-side changes. The server already accepts a returning pid; nothing to do there.
- Offline action queuing. If the user tapped Play right before the drop, that action is lost (the server never received it). Reconnect re-syncs from the server's authoritative state; the user can tap again.
- A "Connection lost — try now" affordance with a manual reopen button. We exponentially back off and try automatically. If we give up, the user refreshes (browser-native UX).
- Re-establishing across tab close / OS-level navigation. `sessionStorage` already dies with the tab; reconnect is purely intra-tab.
- Detecting why we lost the connection (network vs. server kicked us). The close handler doesn't reliably know; trying to reopen is the right move regardless.
- Telemetry/logging of reconnect rates. The server already logs WS open/close at INFO; ops can derive reconnect rate from that.

## Decisions

### Exponential backoff: 1s, 2s, 4s, 8s, 16s, cap 16s

**Choice:** Sleep `min(2^(attempt-1), 16)` seconds before each retry, where `attempt` is 1, 2, 3, … starting fresh after each successful reconnect. So: 1s, 2s, 4s, 8s, 16s, 16s, 16s, …

**Why:** Standard backoff curve. Short initial wait (1s) means a true micro-hiccup is invisible. Cap at 16s prevents the gap from growing unboundedly while we're still trying — the user shouldn't have to wait 60s between attempts.

### Give-up threshold: max(10 attempts, 90s elapsed) — whichever first

**Choice:** Stop trying when either `attempt > 10` OR `Date.now() - firstCloseTs > 90_000`. Show the terminal "Disconnected — refresh to reconnect." banner.

**Why:** With the backoff schedule above, 10 attempts ≈ 1 + 2 + 4 + 8 + 16 × 6 = 111 seconds of attempt time. The 90-second wall clock acts as a defense against tabs that go to background and stop their timers — when the tab resumes we don't want to re-fire 10 instant retries; the elapsed clock catches that. Either condition is fine to terminate on; they're both signals "this isn't a normal hiccup."

### Banner is one `<div>` with three states + hidden

**Choice:** A single fixed-position element (`#conn-banner` desktop, `#m-conn-banner` mobile) that updates text and a state class (`.live` / `.reconnecting` / `.reconnected` / `.lost`). It is `hidden` in the `.live` state.

**Why:** Three different elements would be three CSS rules, three DOM nodes, three places to forget. One element with text content swap keeps the surface area tiny. `role="status"` + `aria-live="polite"` lets screen readers announce changes without being annoying.

### "Reconnected" state flashes briefly then auto-hides

**Choice:** On the first inbound message after a reconnect, show "Reconnected" for 1500 ms, then hide the banner.

**Why:** A silent transition feels broken — "did it actually fix?" The brief confirmation makes the success visible without lingering. Same pattern we use for the share-link "Copied!" flash.

### Action buttons disabled during reconnect

**Choice:** While in the `reconnecting` state, set `disabled=true` on `#play-btn` and `#pickup-btn` (mobile counterparts). Re-enable on receipt of the first inbound message after reopen (which will be a `state` or `lobby` broadcast — the server's resync).

**Why:** A tap during a dead socket either fails silently (no-op) or, worse, looks like it worked because the button responds to its own click. Disabling makes the dead state honest. Re-enable on the server resync rather than on raw socket open — the open event might fire before the server fully accepts us. The first inbound message is the real "OK, you're back" signal.

### Re-use the same `openSocket()` shape; introduce a `scheduleReconnect()` helper

**Choice:** `openSocket()` stays the entry point — same construction, same listeners. The `close` listener's existing tier-1 sentinel-failure path (the `!_wsGotMessage` branch) is unchanged. The else branch — "we *had* a working connection" — now calls a new `scheduleReconnect()` helper instead of writing the terminal label.

**Why:** Keeps the change tightly scoped. The tier-1 path is well-tested and load-bearing for the deep-link auto-join story; we don't want to refactor it. The new helper owns its own attempt counter and timestamp, resets them on success, and calls `openSocket()` recursively when its timer fires.

### Server-side: nothing to do

**Choice:** No `Sec-WebSocket-Close` code refinements, no new endpoints, no `/api/rooms/<code>/heartbeat`.

**Why:** The server's `Room.connect_socket(pid, socket)` already accepts a returning pid (that's the deep-link refresh story). The first broadcast after reconnect resyncs lobby or state. Adding server-side close codes might be nice for diagnostics but is not load-bearing for the user-facing feature. Defer.

### Banner stacks above the existing waiting message

**Choice:** The fixed banner overlays the top of the page; existing `#waiting-message` / `#m-waiting` text in the body stays where it is (and stays empty during reconnect — the banner does the talking).

**Why:** The waiting message lives inside the game/lobby layout. During reconnect we might be on the lobby screen, the setup screen, the game view, or the game-over panel — the banner needs to work uniformly across all of them. Fixed-position is the only sane choice. The existing waiting-message text is repurposed: on a successful reconnect it just goes back to whatever the next broadcast says.

### Reset attempt counter on every successful reconnect

**Choice:** `attemptCount` and `firstCloseTs` reset to `0` / `null` when the next inbound message arrives.

**Why:** A flaky session that drops every few minutes shouldn't accumulate failures across drops. Each disconnect is its own backoff cycle. If the failures *are* clustered (back-to-back fast drops), the wall-clock 90s threshold still catches that case — we won't loop forever.

### Backoff timer is cancellable

**Choice:** Store the timer id; on `openSocket()` success or on terminal-give-up, `clearTimeout` it.

**Why:** Defense against weird races (e.g., user manually closes the tab; we don't want a pending timer to leak). Standard timer hygiene.

### Tab-backgrounding behavior is acceptable

**Choice:** When the tab is backgrounded, `setTimeout` may be throttled and our retries stall. We don't add a `visibilitychange` listener to force-retry on resume.

**Why:** When the tab resumes, the next scheduled retry fires (just later than planned). If by then the 90s wall-clock has passed, we surface the terminal state immediately on that next tick — which is the right outcome (the user has been away long enough that the seat might genuinely be gone). Adding `visibilitychange` handling is extra surface area for a marginal case.

## Risks / Trade-offs

| Risk | Mitigation |
| --- | --- |
| Server has actually evicted the seat (idle timeout, room dead) and we keep retrying for 90s | Backoff caps at 16s and the wall clock is 90s. Three or four wasted retries is cheap. After 90s we show the terminal banner — same outcome as today, just delayed. |
| User taps Play right before the drop, taps again after reconnect, double-plays | Server is authoritative; the first tap never reached it (socket was already dead). The second tap is the only one the server processes. No double-play. |
| Banner flashes "Reconnecting…" for a one-tick blip and disappears, looking glitchy | The first attempt has a 1s delay, so even a micro-hiccup gives the banner ≥ 1s of visibility before "Reconnected" flashes. That reads as honest. |
| `_wsGotMessage` is true but the server has actually evicted us and the new socket also gets immediate-closed | The new socket's `_wsGotMessage` will start as false. Its close handler will hit the tier-1 path: clear sentinel + `location.reload()`. That bumps us to tier 2 (saved-name auto-join) or tier 3 (focused name view). Correct cascading behavior. |
| The Reconnecting banner overlaps the room-code header on mobile and obscures it | The banner is small (≤ 32px tall) and translucent; the underlying layout is still tappable through. We don't disable the body. |
| Race between scheduled retry firing and the user navigating away (closing the tab) | The fired retry creates a new WebSocket which immediately closes when the tab unloads. Browser GC handles it. No leak. |
| `prefers-reduced-motion` users get jarring banner appearances | The banner uses no animation by default — it just appears. Optional opacity fade is gated behind a media query so reduced-motion users still get the simple appear/disappear. |
| Sustained outage where the server is up but our network is down: banner cycles every 16s and feels noisy | After the give-up threshold (10 attempts / 90s) we stop and show terminal. The 90s wall is generous enough that real flakes recover but a truly down network terminates gracefully. |

## Migration Plan

1. **`static/app.js`:**
   - Add a `connState` field to `state` (default `"live"`).
   - Add `setConnState(label)` helper: writes text + a class on `#conn-banner`; toggles `hidden`; toggles `disabled` on `#play-btn` / `#pickup-btn` for `"reconnecting"` and `"lost"` states; clears them for `"live"` / `"reconnected"`.
   - Add `scheduleReconnect()`: tracks `state._reconnectAttempt` (starts at 1), `state._firstCloseTs` (set on first call after the most recent successful connection), computes delay = `Math.min(2 ** (attempt - 1), 16) * 1000` ms, calls `setConnState("reconnecting")`, sets `state._reconnectTimer = setTimeout(openSocket, delay)`.
   - Refactor `openSocket()`:
     - On `message` event: if `state.connState === "reconnecting"`, call `setConnState("reconnected")`, then after 1500 ms call `setConnState("live")`. Reset `_reconnectAttempt = 0`, `_firstCloseTs = null`. Clear `_reconnectTimer`.
     - On `close` event with `!_wsGotMessage`: existing tier-1 reload path (unchanged).
     - On `close` event with `_wsGotMessage`:
       - If first close in this cycle (`_firstCloseTs === null`), set `_firstCloseTs = Date.now()`.
       - If `_reconnectAttempt > 10` OR `Date.now() - _firstCloseTs > 90_000`, call `setConnState("lost")` and return (no more retries).
       - Else `_reconnectAttempt += 1` and call `scheduleReconnect()`.
2. **`static/index.html`:** add `<div id="conn-banner" role="status" aria-live="polite" hidden></div>` as the first child of `<body>`.
3. **`static/styles.css`:** add a small block — fixed top-center, accent background, white text, ≥ 7:1 contrast, drop shadow, optional fade on non-reduced-motion. Add state classes (`.reconnecting`, `.reconnected`, `.lost`) with color tweaks.
4. **`static/mobile.js`:** same refactor against the mobile `openSocket()`. Mobile-specific element ids: `#m-conn-banner`, `#m-play-btn`, `#m-pickup-btn`. The mobile banner respects the safe-area inset at the top.
5. **`static/mobile.html`:** add `<div id="m-conn-banner" role="status" aria-live="polite" hidden></div>` as the first child of `<body>`.
6. **`static/mobile.css`:** mobile banner styling — fixed top, safe-area-aware (`top: env(safe-area-inset-top)`), smaller padding than desktop.
7. **`CHANGELOG.md`** `### Added`: one short entry.
8. **`scripts/smoke_test.py`:** add a reconnect section that uses Playwright's CDP `Network.emulateNetworkConditions(offline=true)` for ~2s then back online, asserting the banner appears as "Reconnecting…", flashes "Reconnected", then hides, and that Play/Pick-up are disabled during the gap.

Rollback: revert the six static files. No server state to migrate.

## Open Questions

- Should we add a `visibilitychange` listener that, when the tab returns to foreground, immediately attempts a reconnect rather than waiting for the current scheduled timer? **Recommendation:** no — risks duplicate retries; the current backoff naturally catches up. Revisit if users report ghost "Disconnected" states after coming back to a tab.
- Should the terminal "Disconnected — refresh to reconnect." banner include a click handler that calls `location.reload()` so the user doesn't have to manually do it? **Recommendation:** yes, but as a tiny tap-anywhere-on-banner gesture, not a separate button. Tracked here for the implementation; small UX win for no extra UI weight. (Specced as optional in the tasks; not enforced in the requirement scenarios.)
- Should we emit a client-side log line (POST to `/api/logs/client` if such an endpoint exists) on each reconnect attempt for ops visibility? **Recommendation:** no — the server's WS open/close already logs at INFO and is sufficient for ops. Adding a client logging endpoint is its own change.
