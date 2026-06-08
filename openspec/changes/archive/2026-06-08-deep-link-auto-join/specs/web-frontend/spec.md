## ADDED Requirements

### Requirement: Auto-join from deep link (desktop)

When the desktop UI loads with `location.pathname` matching `/room/<code>`, the frontend SHALL skip the standard lobby form and attempt to join that room automatically via a three-tier chain:

1. **Session sentinel:** If `sessionStorage.princess_session` exists and its `code` field matches the URL code, the frontend SHALL reopen the WebSocket with the stored `pid`. On success the seated player UI loads directly. On WS rejection (unknown pid, room evicted, etc.) the frontend SHALL fall through to step 2.
2. **Saved name:** If `localStorage.princess_name` is set, the frontend SHALL `POST /api/rooms/<code>/join` with that name. On success it SHALL stash a fresh `princess_session` in sessionStorage and open the WS. On API error it SHALL fall through to step 3.
3. **Focused name view:** A compact view with one input (`#focused-name`) and one button (`Join room <code>`) SHALL be rendered. The standard lobby form (Create/Join buttons + code input) SHALL be hidden. The button SHALL be `disabled` while `#focused-name`'s trimmed value is empty. On submit, the name SHALL be `trim()`-med before being saved to `localStorage.princess_name` and sent to the join API.

On a successful join or successful sentinel reconnect, the frontend SHALL persist:

- `localStorage.princess_name = <name>`
- `sessionStorage.princess_session = JSON.stringify({code, pid, name})`

On a join API failure (404, 409, etc.) at any tier, the frontend SHALL hide the focused view, show the standard lobby with the code prefilled in `#room-code`, and surface the error in `#lobby-error`.

Storage writes SHALL be best-effort (private browsing, quota errors are swallowed silently).

#### Scenario: Auto-join with saved name

- **WHEN** the user (with `localStorage.princess_name = "Mike"`) opens `https://<host>/room/AB12` for a room that exists
- **THEN** the frontend POSTs `/api/rooms/AB12/join` with `name: "Mike"`, opens the WS, and the page enters the seated-player UI without showing any lobby form

#### Scenario: Auto-join shows focused name view when name unknown

- **WHEN** a new visitor opens `https://<host>/room/AB12` and `localStorage.princess_name` is empty
- **THEN** `#focused-join` is visible, the standard lobby (Create/Join + second code input) is hidden, and the focused button text reads `Join room AB12`

#### Scenario: Focused submit saves name + joins

- **WHEN** the focused view is shown, the user types `Pat` and clicks the Join button
- **THEN** `localStorage.princess_name` is `"Pat"`, the POST fires with `name: "Pat"`, and on success the seated UI loads

#### Scenario: Refresh restores host via sentinel

- **WHEN** the host of room AB12 (with `sessionStorage.princess_session = {code: "AB12", pid: "<host_pid>", name: "Mike"}`) refreshes the page
- **THEN** the frontend reopens the WS with `<host_pid>` and the page restores the host's seated UI without creating a new seat

#### Scenario: Join failure falls back to standard lobby

- **WHEN** auto-join is attempted against a room that doesn't exist (`POST /api/rooms/AB12/join` returns 404)
- **THEN** `#focused-join` is hidden, `#room-code` is prefilled with `AB12`, the standard lobby is visible, and `#lobby-error` shows the 404 detail message

#### Scenario: Non-code paths do not auto-join

- **WHEN** the user opens `https://<host>/` (no code in the path)
- **THEN** the standard lobby is shown and no join API call is made

#### Scenario: Join button is disabled with an empty name

- **WHEN** the focused view is rendered with an empty `#focused-name`
- **THEN** the `#focused-join-btn` is `disabled`; typing a non-whitespace character enables it; clearing the input back to empty (or to only spaces) disables it again

#### Scenario: Name is trimmed before save and submit

- **WHEN** the user types `"  Pat  "` and clicks Join
- **THEN** `localStorage.princess_name` is set to `"Pat"` and the POST body has `name: "Pat"` (no leading/trailing whitespace)
