## ADDED Requirements

### Requirement: WebSocket auto-reconnect (desktop)

When a WebSocket that has already received at least one inbound message closes mid-session (the `state._wsGotMessage === true` branch of the close handler), the desktop frontend SHALL automatically attempt to reopen the connection using the SAME `pid` against the same `/ws/<code>/<pid>` URL, applying an exponential-backoff schedule.

**Backoff schedule.** The Nth attempt (N starting at 1) SHALL wait `min(2^(N-1), 16)` seconds before opening a new WebSocket — i.e., 1s, 2s, 4s, 8s, 16s, 16s, 16s, … . The attempt counter SHALL reset to 0 on every successful reconnect (defined as the first inbound message after a reopen).

**Give-up threshold.** If either `attempt > 10` OR `Date.now() - firstCloseTs > 90_000`, the frontend SHALL stop scheduling retries and enter the terminal "lost" state. `firstCloseTs` is the timestamp of the first close event of the current disconnect cycle (cleared on successful reconnect).

**Connection banner.** A single fixed-position element `<div id="conn-banner" role="status" aria-live="polite" hidden>` SHALL surface the connection state:

- `live` state: `hidden`, text empty.
- `reconnecting` state: visible, text reads `Reconnecting…`. The Play (`#play-btn`) and Pick-up (`#pickup-btn`) buttons SHALL be `disabled` while in this state.
- `reconnected` state: visible for approximately 1500 ms, text reads `Reconnected`. After the timeout the banner SHALL return to `live` and hide. Play and Pick-up are re-enabled (subject to normal turn rules) on entry to this state.
- `lost` state (terminal): visible, text reads `Disconnected — refresh to reconnect.` Play and Pick-up remain `disabled`.

The banner SHALL meet WCAG AAA contrast (≥ 7:1 normal-text contrast) and SHALL respect `prefers-reduced-motion` for any optional fade animation.

**Tier-1 sentinel path unchanged.** When the close fires before any inbound message arrived (`state._wsGotMessage === false`), the existing `deep-link-auto-join` behavior SHALL apply (clear `sessionStorage.princess_session` and `location.reload()`). Auto-reconnect SHALL NOT engage on that path.

**Re-sync on reconnect.** After a successful reopen the frontend SHALL render whatever the server's first inbound broadcast (`lobby` or `state`) describes. No client-side merging or stitching of pre/post-disconnect state SHALL be attempted.

**Timer hygiene.** The pending reconnect timer SHALL be cancellable; on a successful reopen or on entry to the terminal `lost` state, any outstanding timer SHALL be cleared.

#### Scenario: Banner appears on mid-session drop

- **WHEN** a desktop session has received at least one `state` broadcast and the WebSocket then closes (e.g., a network blip)
- **THEN** within ≤ 1 second `#conn-banner` becomes visible with text `Reconnecting…`, and both `#play-btn` and `#pickup-btn` are `disabled`

#### Scenario: Single-attempt recovery

- **WHEN** the first reconnect attempt (1s after close) succeeds and the server's first follow-up broadcast arrives
- **THEN** `#conn-banner` text reads `Reconnected`, the banner auto-hides ~1500 ms later, the action buttons re-enable (turn-rules permitting), and the internal attempt counter is back at 0

#### Scenario: Backoff sequence on repeated failure

- **WHEN** the first three reconnect attempts all fail (the new WebSocket closes immediately each time)
- **THEN** the delays between attempts are approximately 1s, 2s, then 4s (each measured from the previous close), and `#conn-banner` remains in the `reconnecting` state throughout

#### Scenario: Backoff caps at 16 seconds

- **WHEN** the 6th, 7th, and 8th attempts are all needed
- **THEN** the delay before each is approximately 16 seconds (not 32, not 64)

#### Scenario: Terminal state after 10 attempts

- **WHEN** 10 consecutive reconnect attempts have failed
- **THEN** `#conn-banner` text reads `Disconnected — refresh to reconnect.`, the banner stays visible, the action buttons remain `disabled`, and no further `setTimeout` for reconnect is scheduled

#### Scenario: Terminal state after 90s wall clock

- **WHEN** the tab was backgrounded mid-disconnect and resumes after 95 seconds with the WebSocket still closed
- **THEN** on the next retry tick the frontend recognizes that `Date.now() - firstCloseTs > 90_000`, enters the terminal `lost` state, and surfaces the "Disconnected — refresh to reconnect." banner without firing further attempts

#### Scenario: Tier-1 sentinel reload is unaffected

- **WHEN** the user opens `/room/AB12` with a stale `sessionStorage.princess_session.pid` and the server closes the WebSocket immediately without sending any message
- **THEN** the existing tier-1 path fires (`sessionStorage` cleared, `location.reload()` invoked) and the new auto-reconnect logic does NOT run

#### Scenario: Action buttons re-enable on resync, not on raw open

- **WHEN** the new WebSocket opens but the server has not yet sent a broadcast
- **THEN** `#play-btn` and `#pickup-btn` remain `disabled`; they re-enable only after the first inbound message arrives (the server's resync of `lobby` or `state`)

#### Scenario: Reconnect uses the same pid

- **WHEN** any auto-reconnect attempt is made
- **THEN** the URL of the new WebSocket is byte-identical to the URL of the dropped one — `/ws/<code>/<pid>` with the same `<pid>` — no new `/api/rooms/<code>/join` call is made

#### Scenario: Banner has accessible roles

- **WHEN** `#conn-banner` enters the `reconnecting` or `lost` state
- **THEN** the element carries `role="status"` and `aria-live="polite"` so screen readers announce the state change without interrupting the user
