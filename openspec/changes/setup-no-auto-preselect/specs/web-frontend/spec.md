## MODIFIED Requirements

### Requirement: Setup phase UI

While `phase == "setup"`, the frontend SHALL hide the game-play surface and render the setup area: three face-down placeholders plus six selectable "choose" cards. The user SHALL be able to toggle exactly three selections. Selecting a fourth replaces the oldest selection. The "Lock in selection" button SHALL be enabled only when exactly three are selected and the user is not already ready.

**No card is ever rendered in a pre-selected state.** On a fresh render of the setup phase — including the initial transition from lobby to setup, a rematch's setup, and any reconnect-driven re-render of setup — every choose card SHALL appear unselected unless the user has explicitly toggled it in this same setup session.

The frontend SHALL reset its in-memory selection set (`state.setupSelected`) whenever the phase transitions into `"setup"` from any other phase (`"lobby"`, `"playing"`, `"game_over"`, or initial page load), provided the player is not already `ready`. The reset SHALL be implemented in `renderGame(view)` by tracking the previous phase and clearing the Set on the transition edge.

Each choose-card `<button>` SHALL carry an `aria-pressed` attribute (`"true"` when in the user's current selection, `"false"` otherwise) so screen readers announce the selection state.

The visual `.selected` style for a choose card SHALL be unambiguously distinct from the gold ★ corner badge that marks wild-rank cards (2, 10, the configured reverse rank). The selected state SHALL render at minimum:

- A thicker accent border than the unselected state.
- A small "✓" or equivalent positively-affirmed glyph in the corner opposite the wild ★ (which lives in the top-right; ✓ lives in the bottom-left).
- An optional upward translate is permitted to reinforce the "lifted" feel; `prefers-reduced-motion` SHALL suppress it.

#### Scenario: Initial render has zero selections

- **WHEN** the host clicks Start, the server broadcasts the first `state` message with `phase: "setup"`, and `renderSetup` runs
- **THEN** no choose card carries the `.selected` class and the "Lock in selection" button is disabled

#### Scenario: Rematch enters setup with a clean Set

- **WHEN** a round ends, the host triggers a rematch, the server broadcasts the new setup state, and `renderGame` routes into the setup branch
- **THEN** `state.setupSelected.size === 0` and no choose card carries `.selected`, regardless of what was selected in the prior round

#### Scenario: Reconnect mid-setup preserves prior in-session selection

- **WHEN** the user is in setup, has selected two cards, and the WebSocket reconnects (state broadcast arrives, `view.phase` is still `"setup"`, `view.you.ready` is false)
- **THEN** the two prior selections survive the re-render (the previous phase was already `"setup"`; no transition edge fires)

#### Scenario: Fourth selection replaces oldest

- **WHEN** three cards are selected and the user clicks a fourth
- **THEN** the first-selected card deselects and the fourth becomes selected, keeping the total at three

#### Scenario: Pending list shows waiting players

- **WHEN** any player has not yet locked in
- **THEN** `#setup-status` reads "Waiting on: <comma-separated names>"

#### Scenario: aria-pressed reflects selection state

- **WHEN** a user toggles a choose card from unselected to selected
- **THEN** the same button's `aria-pressed` attribute flips from `"false"` to `"true"`

#### Scenario: Selected card on a wild rank wears both badges

- **WHEN** a 5 in the choose pile (default reverse rank) is selected
- **THEN** the card displays both the wild ★ glyph (top-right) and the selected ✓ glyph (bottom-left) — they do not overlap and are visually distinct
