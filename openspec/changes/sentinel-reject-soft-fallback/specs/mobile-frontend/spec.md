## MODIFIED Requirements

### Requirement: Auto-join from deep link (mobile)

When the mobile UI loads with `location.pathname` matching `/m/<code>`, the frontend SHALL apply the same three-tier auto-join chain as the desktop UI:

1. **Session sentinel:** `sessionStorage.princess_session` with matching `code` → reopen WS with stored `pid`. **On WebSocket close with `event.code === 4001`** (server signal that the stored pid or room is permanently gone), the frontend SHALL:
   1. Best-effort delete `sessionStorage.princess_session`.
   2. Reset the partially-seated DOM: hide `#m-room` and `#m-game` (toggle `hidden`), show `#m-landing`.
   3. Call `autoJoinFromUrl()` again **in the same page** — re-entering the chain, which now lands at tier 2 (saved name) or tier 3 (focused name view). The frontend SHALL NOT call `location.reload()` in this path.

   On a WebSocket close with `event.code !== 4001` (transient drop), the frontend SHALL NOT clear the sentinel and SHALL NOT re-run `autoJoinFromUrl()` — that path is owned by the separate `websocket-reconnect` change.
2. **Saved name:** `localStorage.princess_name` set → `POST /api/rooms/<code>/join` with that name.
3. **Focused name view:** a compact `<section id="m-focused-join">` showing a name input and a `Join room <code>` button. The standard `#m-landing` create/join controls SHALL be hidden while the focused view is active. The `#m-focused-join-btn` button SHALL be `disabled` while the trimmed value of `#m-focused-name` is empty. On submit, the name SHALL be `trim()`-med before save and send.

On a successful join or sentinel reconnect, the frontend SHALL persist:

- `localStorage.princess_name`
- `sessionStorage.princess_session` (`{code, pid, name}`)

On API failure at any tier, the frontend SHALL hide the focused view, show the standard `#m-landing` view with the code prefilled in `#m-code`, and surface the error via the existing mobile error helper.

The focused view SHALL look at home on a mobile viewport — full-width input and button, no extra chrome — and SHALL respect the 44 × 44 px tap target floor.

Storage writes (and deletions) SHALL be best-effort (private browsing, quota errors are swallowed silently).

#### Scenario: Mobile auto-join with saved name

- **WHEN** the user (with saved name) opens `https://<host>/m/AB12`
- **THEN** the join fires automatically and the seated mobile UI loads with no tap required

#### Scenario: Mobile focused view shown for new visitor

- **WHEN** a new visitor opens `https://<host>/m/AB12`
- **THEN** `#m-focused-join` is visible, the standard landing controls (`#m-create-btn`, `#m-join-btn`, etc.) are hidden, and the focused button reads `Join room AB12`

#### Scenario: Mobile focused submit saves name + joins

- **WHEN** the user types `Pat` in the focused view and taps Join
- **THEN** `localStorage.princess_name` becomes `"Pat"` and the room loads

#### Scenario: Mobile refresh restores via sentinel

- **WHEN** a seated mobile player refreshes their `/m/AB12` page
- **THEN** the frontend reuses the stored `pid` and restores the seat without creating a new join

#### Scenario: Mobile failure falls back to landing

- **WHEN** auto-join receives a 404 for an unknown room
- **THEN** `#m-focused-join` hides, `#m-landing` shows with `#m-code` prefilled and the error visible

#### Scenario: Mobile non-code path does not auto-join

- **WHEN** the user opens `https://<host>/m`
- **THEN** the standard landing controls show, no auto-join API call is made

#### Scenario: Mobile Join button is disabled with an empty name

- **WHEN** the mobile focused view is rendered with an empty `#m-focused-name`
- **THEN** `#m-focused-join-btn` is `disabled`; typing a non-whitespace character enables it; clearing the input back to empty (or to only spaces) disables it again

#### Scenario: Mobile name is trimmed before save and submit

- **WHEN** the user types `"  Pat  "` on the mobile focused view and taps Join
- **THEN** `localStorage.princess_name` is set to `"Pat"` and the POST body has `name: "Pat"`

#### Scenario: Mobile stale sentinel triggers in-page retry, not a reload

- **WHEN** the page loads `/m/AB12` with `sessionStorage.princess_session = {code: "AB12", pid: "stale", name: "Mike"}`, a saved `localStorage.princess_name = "Mike"`, and the server closes the WS with `code=4001` (either `reason="unknown_pid"` or `reason="unknown_room"`)
- **THEN** `sessionStorage.princess_session` is cleared, `#m-room` and `#m-game` are hidden, `#m-landing` is visible, no `location.reload()` is invoked, and the saved-name tier fires in the same page (succeeding if the room exists, or falling through to the standard `#m-landing` with the error visible if not)

#### Scenario: Mobile stale sentinel with no saved name lands on the focused view

- **WHEN** the page loads `/m/AB12` with a stale sentinel and `localStorage.princess_name` is empty, and the server closes with `code=4001`
- **THEN** the sentinel is cleared, the seated DOM is hidden, the mobile landing is restored, and `#m-focused-join` becomes visible (tier 3) — all without a page reload

#### Scenario: Mobile non-4001 close does not trigger the in-page retry

- **WHEN** a successfully-seated mobile player's WebSocket closes with `event.code === 1006`
- **THEN** the frontend does NOT clear `sessionStorage.princess_session` and does NOT re-enter `autoJoinFromUrl()` — the close is treated as transient
