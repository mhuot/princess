## Context

The bot loop in `Room.run_bots()` was capped at 30 actions per call to defend against a buggy `decide()` looping forever (the original freeze that prompted this safety net). The same cap now hurts us in the legitimate "only bots left" case: a fully-bot game just needs to play out to a winner, and 30 actions is rarely enough.

The host's only mid-game exit today is `/abort`, which discards the round without recording any standings. Non-host leavers are silently removed. There's no signal to other humans that someone left, no chance to "let the bots finish for me," and no chance to call the round done so the winner panel can show the current standings.

## Goals / Non-Goals

**Goals:**
- A bot-only room finishes its round without hanging and the room cleans itself up.
- A human leaving mid-round picks from a small menu: convert their seat to a bot, end the round and show the winner panel, or fall back to the existing abandon-to-lobby behavior.
- The host can call the round done explicitly without restarting.
- Registry growth is bounded (no permanent orphans).

**Non-Goals:**
- Reconnect-by-pid persistence (a separate future change). If a human's socket drops without going through the quit modal, this change does not auto-convert them to a bot.
- Per-seat handicaps or "AI takes over with slower think time." The converted seat uses the existing `decide()` at the existing `AI_THINK_SECONDS` cadence.
- Saving the partial round for later resumption.
- A real watchdog thread. The orphan cleanup is opportunistic — runs on each post-action tick — not a separate scheduler.

## Decisions

### Three-option quit modal, not three buttons
**Choice:** Replace the inline "Quit & return to lobby" button's `confirm()` prompt with a small modal that presents the three options as buttons.
**Why:** A one-line `confirm()` can't surface the new options without confusing copy. A real `<dialog>` element gives accessible focus management for free.
**Alternatives:** Three separate buttons in the game-header row — visually loud, easy to misclick.

### Convert-in-place, not remove-and-add
**Choice:** When a leaver picks "Take over with a bot," the existing `Seat` flips `is_bot = True`. Its pid stays the same so the WebSocket closure cleans up naturally. The game's `Player` object — with all its hand, face-up, face-down, finished status, and ready state — is untouched.
**Why:** Preserves the in-progress turn order, hand size, and pile-ownership relationships. Adding a new seat would shuffle turn indices and confuse opponents.
**Trade-off:** The bot inherits whatever cards the human had — including possibly bad face-up choices the bot wouldn't have made. That's acceptable; it's the same constraint we already accept when a bot picks face-up in its own setup-phase auto-pick.

### Cap policy: stay strict while any human is seated, lift when bot-only
**Choice:** `run_bots()` checks `any(seat for seat in self.seats if not seat.is_bot)`. If true, keep the 30-action cap. If false, raise the cap to the lifetime workflow limit (1000) so the round can finish.
**Why:** The cap's only purpose is to keep humans unblocked. With no humans, the only risk is a runaway loop; 1000 is enough headroom for any honest finish.
**Alternative considered:** Always uncap. Rejected — keeps the original safety net intact for any future buggy edit.

### "End the round" calls existing game-over flow
**Choice:** A new `Game.end_round()` method (or a one-line server-side mutation) sets `game_over = True` and appends every still-unfinished player to `finished_order` in **ascending hand-size order** (smaller hand = closer to winning = earlier finish).
**Why:** Reuses every existing renderer (winner banner, finishing order list, rematch button). The hand-size tiebreaker is the most intuitive in-progress proxy for "who's winning right now."
**Trade-off:** Doesn't account for face-up/face-down depth. Adequate for casual ranking.

### Orphan cleanup runs post-action, not on a timer
**Choice:** At the end of `_handle_message` (and after each REST endpoint that touches a room), iterate the registry and drop any room with zero connected sockets older than 5 minutes since last activity.
**Why:** No background tasks, no thread, no schedule — just a simple sweep keyed off `last_activity_ts`. Touches state we already mutate.
**Alternative considered:** An `asyncio.create_task` watchdog loop. Adds lifecycle complexity (start/stop with the app) and isn't needed at this scale.

### `end_round` is host-only, even for non-host leavers
**Choice:** "End the round now" appears in the modal only if the leaver is the host. Non-hosts see "Take over with a bot" and "Abandon (leave only me)."
**Why:** Ending the round affects everyone; only the host should be able to force-end. A non-host who wants to bow out can still let the bots finish.

## Risks / Trade-offs

| Risk | Mitigation |
| --- | --- |
| The 30-cap is still active while ≥1 human is seated, so a buggy `decide()` could still spin briefly | Same as today: force-pickup fallback on engine rejection; `ERROR` log on cap. |
| Orphan sweep deletes a room that's about to receive a fresh connection | 5-minute idle window is generous; an active room sees a write every few seconds during play. |
| Converted-to-bot leaver expected to "play optimally" but inherits a sub-optimal hand | Make the modal copy honest: "The bot picks up where you left off — it'll play what it can with the hand you held." |
| Host clicks "End round" by accident | Modal requires a second click; copy reads "End the round now (show winner with current standings)." |
| Spec change to `room-server` could conflict with show-last-three-moves' web-frontend delta | Both target different requirements; OpenSpec validate confirms no overlap. |

## Migration Plan

1. Engine first: add `Game.end_round()` (a helper, no behavior change otherwise).
2. Server: `LeaveBody.convert_to_bot`, `/end_round` endpoint, `run_bots` cap policy, orphan sweep helper.
3. Frontend: replace the `confirm()` in `quitGame()` with a `<dialog>`-based modal; render "(now a bot)" tag.
4. Tests: leave-as-bot conversion preserves hand; bot-only `run_bots` removes the cap; `/end_round` produces a sensible finishing order; orphan sweep removes idle rooms.
5. Smoke: run a real game, quit-as-bot, confirm bots finish; host-end-round mid-game and confirm winner panel renders.

Rollback: revert the changed files; `LeaveBody.convert_to_bot` is optional with a `False` default so old clients keep working.

## Open Questions

- Should the converted-to-bot seat keep the human's display name, or rename to a bot-roster pick? Current choice: keep the name, add a small "(now a bot)" UI tag.
- Should the host's "End round" surface to a confirm-via-checkbox instead of a single click? Defer until first user complaint.
- Idle timeout of 5 minutes — too short for a friend chat between rounds? Make configurable via env var (`ROOM_IDLE_TIMEOUT_SECONDS`, default 300)?
