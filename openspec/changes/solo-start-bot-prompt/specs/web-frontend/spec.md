## MODIFIED Requirements

### Requirement: Lobby renders seats and host controls

In the room view the frontend SHALL render: the room code, the list of seats with host/bot/offline badges, a "House rules" config panel, and (for the host only) Add-bot and Start-game buttons. Non-hosts SHALL see the config controls as `disabled` with a note that only the host can change them.

Each seat row SHALL render zero, one, or two per-row controls:

- A **Remove** button on **bot rows**, visible to the host only. Clicking it posts to `/api/rooms/<code>/remove_bot` with the bot's pid and the host's pid; on success the lobby re-renders and the seat is gone.
- A **Rename** button on the **caller's own seat row** (whether host or non-host). Clicking it replaces the seat's name with an inline `<input type="text" maxlength="20">` pre-filled with the current name. Pressing Enter (or blurring the input with a non-empty value) submits to `/api/rooms/<code>/rename` with the caller's pid; Escape cancels. On success the lobby re-renders.

Non-callers do NOT see the Rename button on someone else's row. Non-hosts do NOT see Remove on bot rows.

The House rules panel SHALL contain the **Reverse rank** `<select>` (as previously specified). Changing it triggers `POST /api/rooms/<code>/config`.

When the host clicks **Start game**, the frontend SHALL inspect `room.seats.length` from the most recent lobby broadcast. If exactly **1** (the host is alone), the frontend SHALL open a centered `<dialog>` modal titled "You're alone in the room." offering three primary actions — **Add 1 bot**, **Add 2 bots**, **Add 3 bots** — plus a **Back to lobby** button. On a primary action, the frontend SHALL sequentially `POST /api/rooms/{code}/bot` `N` times and, on success, `POST /api/rooms/{code}/start`. On any `POST /bot` failure, the frontend SHALL surface the error in the existing lobby-error slot and SHALL NOT POST `/start`. If `room.seats.length >= 2`, the frontend SHALL NOT open the modal and SHALL post `/start` directly as today.

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
