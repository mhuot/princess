## MODIFIED Requirements

### Requirement: Lobby renders seats and host controls

In the room view the frontend SHALL render: the room code, the list of seats with host/bot/offline badges, a "House rules" config panel, and (for the host only) Add-bot and Start-game buttons. Non-hosts SHALL see the config controls as `disabled` with a note that only the host can change them.

Each seat row SHALL render zero, one, or two per-row controls:

- A **Remove** button on **bot rows**, visible to the host only. Clicking it posts to `/api/rooms/<code>/remove_bot` with the bot's pid and the host's pid; on success the lobby re-renders and the seat is gone.
- A **Rename** button on the **caller's own seat row** (whether host or non-host). Clicking it replaces the seat's name with an inline `<input type="text" maxlength="20">` pre-filled with the current name.

Non-callers do NOT see the Rename button on someone else's row. Non-hosts do NOT see Remove on bot rows.

The inline Rename input SHALL behave as follows:

- **Escape** cancels: the input collapses back to the original name and no network call is made.
- **Enter** (or **blur with a changed non-empty value**) submits to `POST /api/rooms/<code>/rename` with the caller's pid and the trimmed value. While the POST is in flight, the input SHALL be `disabled` to prevent double-submit; the input SHALL remain in the DOM (it SHALL NOT be replaced with the static name span until the response resolves).
- **On a 2xx response**, the input SHALL be replaced with the lobby's standard name span. Any error currently shown in `#lobby-error` from a prior failed attempt SHALL be cleared.
- **On any 4xx response** (including **409 Conflict** when the name collides with another seat, and **422 Unprocessable Entity** when validation fails), the input SHALL remain in the DOM, the error SHALL surface in `#lobby-error` using the existing helper (`showError("lobby-error", e.message)`), the input SHALL be re-enabled, re-focused, and its contents SHALL be programmatically selected (`input.focus(); input.select()`) so the user can immediately type a replacement value without clicking Rename again.
- **Blur with an unchanged value** is a no-op cancel: the input collapses without a POST.

The House rules panel SHALL contain the **Reverse rank** `<select>` (as previously specified). Changing it triggers `POST /api/rooms/<code>/config`.

The House rules panel SHALL contain at minimum the **Reverse rank** `<select>` whose options list the legal reverse ranks (3, 4, 5, 6, 7, 8, 9, J, Q, K, A). The displayed text uses the human label (J/Q/K/A) but the submitted value is the integer rank (11/12/13/14). The panel SHALL NOT include a "same rank on reverse" control — the reverse rank is always legal as a wild.

Changing the dropdown SHALL trigger a `POST /api/rooms/<code>/config` containing `{"reverse_rank": <int>}`. Non-hosts see the control disabled with the existing `#config-readonly-note`.

When the host clicks **Start game**, the frontend SHALL inspect `room.seats.length` from the most recent lobby broadcast. If exactly **1** (the host is alone), the frontend SHALL open a centered `<dialog id="solo-start-modal">` modal titled "You're alone in the room." offering three primary actions — **Add 1 bot**, **Add 2 bots**, **Add 3 bots** — plus a **Back to lobby** button. On a primary action, the frontend SHALL sequentially `POST /api/rooms/{code}/bot` `N` times and, on success, `POST /api/rooms/{code}/start`. On any `POST /bot` failure, the frontend SHALL surface the error in the existing lobby-error slot and SHALL NOT POST `/start`. If `room.seats.length >= 2`, the frontend SHALL NOT open the modal and SHALL post `/start` directly as today.

#### Scenario: Non-host sees disabled control

- **WHEN** a non-host renders the lobby
- **THEN** the `<select>` for reverse rank is `disabled` and `#config-readonly-note` is visible

#### Scenario: Selecting K posts the correct integer

- **WHEN** the host changes the dropdown to "K"
- **THEN** the `POST /api/rooms/<code>/config` body is `{"host_pid": …, "config": {"reverse_rank": 13}}`

#### Scenario: Default selection is 5

- **WHEN** a fresh lobby is rendered with no prior config change
- **THEN** the dropdown shows "5" selected

#### Scenario: No same-on-reverse checkbox

- **WHEN** the House rules panel is rendered
- **THEN** there is no element with id `cfg-same-on-reverse`

#### Scenario: Solo start opens the bot prompt

- **WHEN** the host is the only seated player and clicks Start game
- **THEN** the `#solo-start-modal` `<dialog>` opens with three "Add N bot(s)" buttons and a "Back to lobby" button

#### Scenario: Add 2 bots and start

- **WHEN** the host clicks "Add 2 bots" in the solo-start modal
- **THEN** the frontend POSTs `/api/rooms/<code>/bot` twice in sequence, then POSTs `/api/rooms/<code>/start`, then the modal closes

#### Scenario: Back to lobby leaves the room unchanged

- **WHEN** the host clicks "Back to lobby" in the solo-start modal
- **THEN** the modal closes; no POSTs are made; the host remains on the lobby in its prior state

#### Scenario: No prompt when a bot is already seated

- **WHEN** the host has one bot in the room and clicks Start game
- **THEN** the modal does NOT open and `/api/rooms/<code>/start` is posted as today

#### Scenario: Bot add failure aborts auto-start

- **WHEN** the host clicks "Add 3 bots" and the second `POST /bot` fails (e.g., 409 room full)
- **THEN** the frontend surfaces the error in the lobby-error slot, does NOT post `/start`, and leaves any successfully-added bots in the room

#### Scenario: Host sees Remove on bot rows

- **WHEN** the host renders a lobby containing two bot seats
- **THEN** each bot row carries a Remove button; the host's own row does not carry one

#### Scenario: Non-host does NOT see Remove on bot rows

- **WHEN** a non-host renders the same lobby
- **THEN** no bot row carries a Remove button

#### Scenario: Caller sees Rename on their own row only

- **WHEN** a non-host renders a lobby with the host and two bots
- **THEN** the non-host's own row carries a Rename button; the host's row and the bot rows do not

#### Scenario: Rename input cancels on Escape

- **WHEN** the user clicks Rename, edits the input, then presses Escape
- **THEN** the input collapses back to the original name and no network call is made

#### Scenario: Rename input stays open on a 409 collision

- **WHEN** a non-host named "Pat" clicks Rename, types "Mike" (the host's name), and presses Enter
- **THEN** the rename POST returns 409, `#lobby-error` shows the server's `"name 'Mike' is already taken in this room"` message, the inline `<input>` remains in the DOM, is re-enabled, is focused, and its full value "Mike" is selected so the user can type over it without clicking Rename again

#### Scenario: Rename input stays open on a 422 overlength

- **WHEN** the user clicks Rename and submits a name longer than 20 characters (somehow bypassing `maxlength` — e.g., paste-and-Enter on a browser that briefly exceeds the cap before truncation)
- **THEN** the POST returns 422, `#lobby-error` shows the validation message, the input remains in the DOM, is re-enabled, is focused, and its contents are selected

#### Scenario: Successful rename collapses the input and clears prior error

- **WHEN** the user previously saw a 409 (with the input still open) and now types a non-conflicting name and presses Enter
- **THEN** the POST returns 200, the inline input is removed in favor of the standard name span, and any prior `#lobby-error` message is cleared

#### Scenario: Input is disabled while the rename POST is in flight

- **WHEN** the user presses Enter to submit a rename
- **THEN** the `<input>` element's `disabled` attribute is `true` for the duration of the POST; on response (success or failure) the disabled state is removed before any focus/select call
