## MODIFIED Requirements

### Requirement: Mobile lobby

The mobile lobby SHALL provide: name input, **Create new room** button, room-code input, **Join room** button. Once in a room, the lobby SHALL list seats with name + host/bot/offline tags + the caller's own Rename inline-input control.

The mobile lobby SHALL NOT include the House rules config controls. The current reverse rank SHALL be displayed as read-only text ("Reverse rank: 5"). The host on mobile SHALL be able to add a bot (single Add bot button) and Start the game; bot removal SHALL NOT be available on mobile (defer to desktop).

When the host taps **Start game** on the mobile lobby, the frontend SHALL inspect the most recent lobby broadcast's `room.seats.length`. If exactly **1** (the host is alone), the frontend SHALL open a bottom-sheet `<dialog id="m-solo-sheet" class="m-sheet">` titled "You're alone in the room." offering three primary actions — **Add 1 bot**, **Add 2 bots**, **Add 3 bots** — plus a **Back to lobby** button. On a primary action, the frontend SHALL sequentially `POST /api/rooms/{code}/bot` `N` times and then `POST /api/rooms/{code}/start`. On any `POST /bot` failure, the frontend SHALL surface the error via the existing lobby error helper and SHALL NOT post `/start`. If `seats.length >= 2`, the frontend SHALL skip the sheet and post `/start` directly.

#### Scenario: Mobile lobby has no House rules controls

- **WHEN** a non-host renders the mobile lobby
- **THEN** no element with id `cfg-reverse-rank` or matching the desktop's House rules panel is present

#### Scenario: Host can Add bot and Start

- **WHEN** the host renders the mobile lobby
- **THEN** an **Add bot** button and a **Start game** button are visible

#### Scenario: Reverse rank shown as read-only

- **WHEN** any user renders the mobile lobby
- **THEN** a small "Reverse rank: <rank>" label is shown

#### Scenario: Solo start opens the bottom sheet

- **WHEN** the host is the only seated player on mobile and taps Start game
- **THEN** the `#m-solo-sheet` `<dialog>` opens as a bottom sheet with three "Add N bot(s)" buttons and a "Back to lobby" button

#### Scenario: Mobile Add 2 bots and start

- **WHEN** the host taps "Add 2 bots" in the mobile solo-start sheet
- **THEN** the frontend POSTs `/api/rooms/<code>/bot` twice in sequence, then POSTs `/api/rooms/<code>/start`, then the sheet closes

#### Scenario: Mobile back-to-lobby leaves the room unchanged

- **WHEN** the host taps "Back to lobby" in the mobile solo-start sheet
- **THEN** the sheet closes; no POSTs are made; the host remains on the lobby in its prior state

#### Scenario: Mobile no prompt when a bot is already seated

- **WHEN** the host has one bot in the room and taps Start game on mobile
- **THEN** the sheet does NOT open and `/api/rooms/<code>/start` is posted directly
