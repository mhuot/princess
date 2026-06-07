## Why

Observed bug: in a room with humans + bots, when the last human leaves mid-game, the room becomes "all bots." The bot loop's 30-action safety cap (added to prevent infinite loops) fires, halts, and the room hangs. There's no human left to drive the WebSocket, but the room sits in the registry forever holding state.

Also missing: when a human leaves or the host aborts mid-game, neither the leaver nor the remaining humans get any choice about what should happen to the in-flight round. The host's only "exit" today is `/abort`, which dumps everyone back to the lobby with no record of the round's progress. A non-host leaver removes themselves silently with no notice to others.

This change adds end-of-round options at the quit moment, replaces the leaving human's seat with a bot if the game continues, and cleans up bot-only rooms so they can't hang.

## What Changes

- **Quit dialog (frontend):** the existing "Quit & return to lobby" button opens a small modal with up to three options depending on context:
  - **Take over with a bot (continue the round)** — the current player's seat converts to a bot; the round keeps playing for the other humans. New default for non-host quitters mid-round.
  - **End the round now** — declare current finishing order as the result and show the winner banner to all players. Available to host only; in-progress humans are appended to `finished_order` in their current standing order (hand-size ascending: fewer cards = higher finish). Replaces the host's "abort to lobby" path during a live game.
  - **Abandon and return to lobby** — current behavior (host aborts the game; everyone goes back to the lobby). Still available for the host.
- **Bot seat conversion (server):** new `POST /api/rooms/{code}/leave` flag `convert_to_bot: bool`. When true, the seat is flipped to a bot in place (keep pid + hand + history) so the game can continue. The new bot picks up the leaver's hand and plays it out using the existing `decide()`.
- **Bot-only auto-resolve (server):** when `run_bots()` finds no human seats remaining in a playing game, it raises the per-call action cap from 30 to `unlimited` and runs the round to completion (limited only by the lifetime cap of 1000). On completion the room is marked `closed` and dropped from the registry on next tick.
- **End-of-round-now action (server):** new `POST /api/rooms/{code}/end_round` host-only that synthesizes a `game_over = True` with `finished_order` built from already-finished players + remaining-by-hand-size. Broadcast as the normal game-over state so the winner panel renders.
- **Orphan watchdog (server):** a lightweight loop (or post-action check) removes any room whose seats are all `socket is None` AND no game is in progress for > 5 minutes. Prevents indefinite registry growth.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `room-server`:
  - Add `end_round` endpoint and the `convert_to_bot` flag on `/leave`.
  - Adjust `run_bots()` cap policy: 30 actions/turn while humans are seated; effectively unlimited (cap = 1000 lifetime) when only bots remain.
  - Add the orphan-room cleanup behavior.
- `ai-bot`:
  - Allow `run_bots()` to run uncapped in bot-only rooms so it can finish the round.
  - Specify the bot-takeover behavior for a converted seat (same `decide()`; carries over hand/face-up/face-down).
- `web-frontend`:
  - Replace the single quit confirmation prompt with a modal offering the three options above.
  - When a peer is replaced by a bot mid-round, the broadcast lobby/state already carries the `is_bot` flag — the UI shows a small "(now a bot)" tag next to that name for the rest of the round.

## Impact

- **Affected code:**
  - `princess/rooms.py` — `run_bots` cap logic, leave-as-bot path, orphan watchdog.
  - `princess/server.py` — new `/end_round` endpoint, `LeaveBody.convert_to_bot`.
  - `static/index.html`, `static/app.js`, `static/styles.css` — quit modal UI + "(now a bot)" tag.
- **Affected APIs:** new `/end_round`; `/leave` gains optional `convert_to_bot` (default `false` keeps the existing remove-seat behavior).
- **Affected dependencies:** none.
- **Depends on:** baseline-princess-card-game archived (modifies `room-server`, `ai-bot`, `web-frontend`).
- **Not in this change:** any client-side reconnect-by-pid persistence (separate change); replacing humans with bots automatically on socket-drop (this is opt-in via the quit modal).
