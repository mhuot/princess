## ADDED Requirements

### Requirement: Auto-join from deep link (mobile)

When the mobile UI loads with `location.pathname` matching `/m/<code>`, the frontend SHALL apply the same three-tier auto-join chain as the desktop UI:

1. **Session sentinel:** `sessionStorage.princess_session` with matching `code` → reopen WS with stored `pid`.
2. **Saved name:** `localStorage.princess_name` set → `POST /api/rooms/<code>/join` with that name.
3. **Focused name view:** a compact `<section id="m-focused-join">` showing a name input and a `Join room <code>` button. The standard `#m-landing` create/join controls SHALL be hidden while the focused view is active. The `#m-focused-join-btn` button SHALL be `disabled` while the trimmed value of `#m-focused-name` is empty. On submit, the name SHALL be `trim()`-med before save and send.

On a successful join or sentinel reconnect, the frontend SHALL persist:

- `localStorage.princess_name`
- `sessionStorage.princess_session` (`{code, pid, name}`)

On API failure at any tier, the frontend SHALL hide the focused view, show the standard `#m-landing` view with the code prefilled in `#m-code`, and surface the error via the existing mobile error helper.

The focused view SHALL look at home on a mobile viewport — full-width input and button, no extra chrome — and SHALL respect the 44 × 44 px tap target floor.

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
