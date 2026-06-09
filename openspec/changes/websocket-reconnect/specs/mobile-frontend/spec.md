## ADDED Requirements

### Requirement: WebSocket auto-reconnect (mobile)

When a WebSocket on the mobile UI that has already received at least one inbound message closes mid-session (the `state._wsGotMessage === true` branch of the close handler), the mobile frontend SHALL automatically attempt to reopen the connection using the SAME `pid` against the same `/ws/<code>/<pid>` URL, applying the same exponential-backoff schedule as the desktop UI.

**Backoff schedule.** The Nth attempt (N starting at 1) SHALL wait `min(2^(N-1), 16)` seconds before opening a new WebSocket — i.e., 1s, 2s, 4s, 8s, 16s, 16s, 16s, … . The attempt counter SHALL reset to 0 on every successful reconnect.

**Give-up threshold.** If either `attempt > 10` OR `Date.now() - firstCloseTs > 90_000`, the mobile frontend SHALL stop scheduling retries and enter the terminal `lost` state.

**Connection banner.** A single fixed-position element `<div id="m-conn-banner" role="status" aria-live="polite" hidden>` SHALL surface the connection state at the top of the viewport, respecting the top safe-area inset (`env(safe-area-inset-top)`):

- `live` state: `hidden`, text empty.
- `reconnecting` state: visible, text reads `Reconnecting…`. The mobile Play (`#m-play-btn`) and Pick-up (`#m-pickup-btn`) buttons SHALL be `disabled` while in this state.
- `reconnected` state: visible for approximately 1500 ms, text reads `Reconnected`. After the timeout the banner SHALL return to `live` and hide. Play and Pick-up are re-enabled (subject to normal turn rules) on entry to this state.
- `lost` state (terminal): visible, text reads `Disconnected — refresh to reconnect.`. Play and Pick-up remain `disabled`.

The banner SHALL meet WCAG AAA contrast (≥ 7:1 normal-text contrast) and SHALL respect `prefers-reduced-motion` for any optional fade animation. Because the banner is not interactive, it MAY render at less than 44 × 44 px.

**Tier-1 sentinel path unchanged.** When the close fires before any inbound message arrived (`state._wsGotMessage === false`), the existing `deep-link-auto-join` behavior SHALL apply (clear `sessionStorage.princess_session` and `location.reload()`). Auto-reconnect SHALL NOT engage on that path.

**Re-sync on reconnect.** After a successful reopen the mobile frontend SHALL render whatever the server's first inbound broadcast (`lobby` or `state`) describes. No client-side merging or stitching of pre/post-disconnect state SHALL be attempted.

**Timer hygiene.** The pending reconnect timer SHALL be cancellable; on a successful reopen or on entry to the terminal `lost` state, any outstanding timer SHALL be cleared.

**Sticky action bar interaction.** The mobile sticky action bar's Play and Pick-up buttons SHALL show their `disabled` visual treatment during reconnect (lower opacity, no tap feedback), matching the existing disabled state used when it is not the user's turn.

#### Scenario: Mobile banner appears on mid-session drop

- **WHEN** a mobile session has received at least one `state` broadcast and the WebSocket then closes (e.g., a signal blip on cellular)
- **THEN** within ≤ 1 second `#m-conn-banner` becomes visible with text `Reconnecting…`, and both `#m-play-btn` and `#m-pickup-btn` are `disabled`

#### Scenario: Mobile single-attempt recovery

- **WHEN** the first reconnect attempt succeeds and the server's first follow-up broadcast arrives
- **THEN** `#m-conn-banner` text reads `Reconnected`, the banner auto-hides ~1500 ms later, the action buttons re-enable (turn-rules permitting), and the internal attempt counter is back at 0

#### Scenario: Mobile backoff caps at 16 seconds

- **WHEN** the 6th, 7th, and 8th attempts are all needed
- **THEN** the delay before each is approximately 16 seconds (not 32, not 64)

#### Scenario: Mobile terminal state after 10 attempts

- **WHEN** 10 consecutive reconnect attempts have failed
- **THEN** `#m-conn-banner` text reads `Disconnected — refresh to reconnect.`, the banner stays visible, `#m-play-btn` and `#m-pickup-btn` remain `disabled`, and no further `setTimeout` for reconnect is scheduled

#### Scenario: Mobile terminal state after 90s wall clock

- **WHEN** the tab was backgrounded mid-disconnect and resumes after 95 seconds with the WebSocket still closed
- **THEN** on the next retry tick the mobile frontend recognizes that `Date.now() - firstCloseTs > 90_000`, enters the terminal `lost` state, and surfaces the "Disconnected — refresh to reconnect." banner without firing further attempts

#### Scenario: Mobile tier-1 sentinel reload is unaffected

- **WHEN** the user opens `/m/AB12` with a stale `sessionStorage.princess_session.pid` and the server closes the WebSocket immediately without sending any message
- **THEN** the existing tier-1 path fires (sentinel cleared, `location.reload()` invoked) and the new auto-reconnect logic does NOT run

#### Scenario: Mobile reconnect uses the same pid

- **WHEN** any auto-reconnect attempt is made on mobile
- **THEN** the new WebSocket URL equals the dropped URL — `/ws/<code>/<pid>` with the same `<pid>` — no new `POST /api/rooms/<code>/join` call is made

#### Scenario: Mobile banner respects top safe-area inset

- **WHEN** the mobile UI is rendered on a device with a top safe-area inset (e.g., iPhone with notch)
- **THEN** `#m-conn-banner` is positioned with `top: env(safe-area-inset-top)` so it does not overlap with the status bar

#### Scenario: Mobile action buttons re-enable on resync, not on raw open

- **WHEN** the new WebSocket opens but the server has not yet sent a broadcast
- **THEN** `#m-play-btn` and `#m-pickup-btn` remain `disabled`; they re-enable only after the first inbound message arrives (the server's resync of `lobby` or `state`)

#### Scenario: Mobile banner has accessible roles

- **WHEN** `#m-conn-banner` enters the `reconnecting` or `lost` state
- **THEN** the element carries `role="status"` and `aria-live="polite"` so screen readers announce the state change without interrupting the user
