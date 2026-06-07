## MODIFIED Requirements

### Requirement: Lobby renders seats and host controls

In the room view the frontend SHALL render: the room code, the list of seats with host/bot/offline badges, a "House rules" config panel, and (for the host only) Add-bot and Start-game buttons. Non-hosts SHALL see the config controls as `disabled` with a note that only the host can change them.

Each seat row SHALL render zero, one, or two per-row controls:

- A **Remove** button on **bot rows**, visible to the host only. Clicking it posts to `/api/rooms/<code>/remove_bot` with the bot's pid and the host's pid; on success the lobby re-renders and the seat is gone.
- A **Rename** button on the **caller's own seat row** (whether host or non-host). Clicking it replaces the seat's name with an inline `<input type="text" maxlength="20">` pre-filled with the current name. Pressing Enter (or blurring the input with a non-empty value) submits to `/api/rooms/<code>/rename` with the caller's pid; Escape cancels. On success the lobby re-renders.

Non-callers do NOT see the Rename button on someone else's row. Non-hosts do NOT see Remove on bot rows.

The House rules panel SHALL contain the **Reverse rank** `<select>` (as previously specified). Changing it triggers `POST /api/rooms/<code>/config`.

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

### Requirement: Quit & return to lobby

During an in-progress game the frontend SHALL display a red-bordered "Quit & return to lobby" button. Clicking it SHALL open a small modal (`<dialog>` element with focus management) presenting up to three actions instead of a single confirm prompt:

- **Take over with a bot (continue the round)** — visible to non-host players. Closes the modal, POSTs `/leave` with `convert_to_bot: true`, then closes the WebSocket and redirects the user to `/`. Other players see the seat continue as a bot for the rest of the round.
- **End the round now** — visible to the host only. Closes the modal and POSTs `/end_round`. The user remains in the room; the broadcast game-over state triggers the winner panel for everyone.
- **Abandon and return to lobby** — visible to the host (as "Abort the game"). Closes the modal and POSTs `/abort`; the room returns to the lobby phase. For non-hosts this option is labelled "Leave room" and POSTs `/leave` with `convert_to_bot: false`, redirecting the user to `/` and removing their seat entirely.

The modal SHALL be keyboard accessible: `Esc` closes without action, the first action button is auto-focused, and `Tab` cycles through the available actions.

The game-view header SHALL also expose a small **Rename** button. Clicking it SHALL prompt the user (via a browser `prompt()` or an inline input) for a new name; on confirm the frontend SHALL POST `/api/rooms/<code>/rename` with the caller's pid and the new name. The broadcast state update reflects the new name to all opponents.

#### Scenario: Non-host opens the modal

- **WHEN** a non-host clicks Quit during a live game
- **THEN** the modal shows "Take over with a bot (continue the round)" and "Leave room"; "End the round now" is not present

#### Scenario: Host opens the modal

- **WHEN** the host clicks Quit during a live game
- **THEN** the modal shows "End the round now" and "Abort the game" but does NOT show "Take over with a bot"

#### Scenario: Non-host bot takeover

- **WHEN** a non-host picks "Take over with a bot (continue the round)"
- **THEN** the browser POSTs `/api/rooms/<code>/leave` with `convert_to_bot: true`, closes the WebSocket, and navigates to `/`

#### Scenario: Host ends the round

- **WHEN** the host picks "End the round now"
- **THEN** the browser POSTs `/api/rooms/<code>/end_round`; the next broadcast renders the winner panel for everyone, including the host

#### Scenario: Esc cancels with no action

- **WHEN** the modal is open and the user presses Escape
- **THEN** the modal closes and no network call is made

#### Scenario: Mid-round rename succeeds

- **WHEN** a player clicks the game-header Rename button and confirms a new valid name
- **THEN** the browser POSTs `/api/rooms/<code>/rename`; the next broadcast state shows the new name in the opponent rows for the other players
