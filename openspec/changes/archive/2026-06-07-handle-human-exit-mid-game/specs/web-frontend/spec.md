## MODIFIED Requirements

### Requirement: Quit & return to lobby

During an in-progress game the frontend SHALL display a red-bordered "Quit & return to lobby" button. Clicking it SHALL open a small modal (`<dialog>` element with focus management) presenting up to three actions instead of a single confirm prompt:

- **Take over with a bot (continue the round)** — visible to non-host players. Closes the modal, POSTs `/leave` with `convert_to_bot: true`, then closes the WebSocket and redirects the user to `/`. Other players see the seat continue as a bot for the rest of the round.
- **End the round now** — visible to the host only. Closes the modal and POSTs `/end_round`. The user remains in the room; the broadcast game-over state triggers the winner panel for everyone.
- **Abandon and return to lobby** — visible to the host (as "Abort the game"). Closes the modal and POSTs `/abort`; the room returns to the lobby phase. For non-hosts this option is labelled "Leave room" and POSTs `/leave` with `convert_to_bot: false`, redirecting the user to `/` and removing their seat entirely.

The modal SHALL be keyboard accessible: `Esc` closes without action, the first action button is auto-focused, and `Tab` cycles through the available actions.

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

## ADDED Requirements

### Requirement: "Now a bot" tag

When a seat in the room has `is_bot == true`, the frontend SHALL render a small "(bot)" or "(now a bot)" tag next to the name. The tag SHALL be present in the opponents row during play and in the lobby seat list before the game starts. For a seat that started as a human and was converted mid-round, the tag SHALL read "(now a bot)" so the change is obvious; for seats that were bots from the start, the tag SHALL read "(bot)".

The frontend SHALL infer "started as human" by tracking the seat's prior `is_bot` flag in client state — if it was `false` on a previous render and is now `true`, the "now a bot" variant applies for the rest of the round.

#### Scenario: Original bot tagged as "(bot)"

- **WHEN** a seat has been a bot from creation
- **THEN** the opponent name renders followed by " (bot)"

#### Scenario: Converted human tagged as "(now a bot)"

- **WHEN** a seat flips from `is_bot: false` to `is_bot: true` mid-round
- **THEN** the opponent name renders followed by " (now a bot)" until the round ends
