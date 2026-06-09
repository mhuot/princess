## Context

Princess is single-process in-memory by design. Rooms live in `RoomRegistry`, get evicted by the idle sweep after 5 min of disconnect, and have no persistent backing. Within that lifetime a room can host any number of rounds via `/rematch`, which today calls `Room.reset_for_rematch()` (sets `self.game = None`) and re-runs `start_game()` against the existing seats. Every rematch starts the engine fresh — there is no memory of the prior round's `finished_order`.

The natural place for session-level scoreboard state is `Room`, not `Game`. Rationale: the engine is round-scoped (it intentionally resets per round) and round-aware (it tracks the in-progress `finished_order`). The room is session-scoped (it persists seats, config, and now scores across rematches). Keeping scoreboard outside `Game` also means the engine's pure-rules-core contract stays untouched — no test fixtures or pure-Python tests need to learn a new field.

The bump happens at the room layer, triggered when the engine reports `game_over`. The room layer is already the only thing that observes the game-over transition (it drives `broadcast_state`, which calls `view_for(pid)`).

## Goals / Non-Goals

**Goals:**
- Per-seat counters for Princess wins, last places, and rounds played.
- Counters persist across rematches within the same room lifetime.
- Counters reset on `/abort` and on room eviction.
- A removed seat (via `/remove_bot` or human-leave-without-bot) loses its entry.
- Surfaced in `lobby` and `state` broadcasts so both UIs see it without a separate request.
- Idempotent: a re-broadcast of the same finished game must not double-count.
- Both UIs render the scoreboard in two places: the winner panel and the opponent name badge.

**Non-Goals:**
- Persistence (no database, no localStorage on the server side).
- Cross-room session continuity (a player who creates a new room loses prior session counts).
- More-than-two ranks ("middle place", "second", etc.). Princess and last place are the two named ranks; everything else is a count of rounds played.
- Animations or fanfare on bump.
- A separate "session history" log of past rounds. The counters are the entire signal.
- Anonymous spectator views — only seated players see the scoreboard.

## Decisions

### Scoreboard lives on `Room`, not on `Game`
**Choice:** `Room.scoreboard: dict[str, dict[str, int]]` keyed by pid.
**Why:** Game is round-scoped and gets thrown away on rematch. Room is the session-scoped owner. Placing the dict on Room means the engine stays pure and no engine-level tests need updating.

### Three counters per seat
**Choice:** `princess_wins`, `last_places`, `rounds_played`.
**Why:** The proposal calls out "Princess wins" as the primary signal and "last places" as a soft secondary. `rounds_played` is needed for the winner-panel summary line ("Princess 3 · Last place 1 · 4 rounds") so the user can tell whether the 3 wins came from 3 rounds (sweep) or 10 (one in three).

### Initialized on seat creation, dropped on seat removal
**Choice:** Add a fresh `{princess_wins: 0, last_places: 0, rounds_played: 0}` entry whenever a seat joins (`/api/rooms`, `/join`, `/bot`, or convert-to-bot). Drop the entry on `/remove_bot` and on `/leave` (without `convert_to_bot`). On convert-to-bot, the entry is preserved (same pid, same seat, only `is_bot` flips).
**Why:** Keeps the dict tight to actual seats. A re-add at the same name later starts fresh because it's a new pid.

### Bump on the game-over edge, not on every state broadcast
**Choice:** A `Room._scoreboard_round_id` (or equivalent flag) tracks the most recent round whose final state was already counted. On each broadcast, if `game.game_over` is `True` and the round hasn't been counted yet, the bump fires once and the flag is set. The flag clears on `start_game` (and on rematch's fresh `start_game`).
**Why:** State broadcasts can fire multiple times for the same `game_over` state (e.g., on a reconnect, on `/end_round` for the host, when the rematch button render triggers a re-broadcast). The bump must be idempotent.

### Reset on `/abort`, NOT on `/rematch`
**Choice:** `/abort` zeroes every seat's counters back to `{0, 0, 0}`. `/rematch` leaves them untouched.
**Why:** The whole point of the change is that rematches accumulate. `/abort` is the explicit "this session is over" signal — pairing the scoreboard reset with it gives the host a clear way to start the score fresh without making them recreate the room.

### Lobby and state both carry the scoreboard
**Choice:**
- `Room.public_lobby()` adds `"scoreboard": {pid: {...}, ...}` next to `seats`.
- The per-seat state envelope (the WebSocket `{type: "state", view: ...}` message) gains a top-level `"scoreboard"` field alongside `view`, populated from `Room.scoreboard`.
**Why:** Both UIs render seats in both contexts. Putting it on the envelope (not inside `view`) keeps `Game.view_for(pid)` untouched. Clients read `msg.scoreboard` or `msg.room.scoreboard` depending on the message type.

### Render layer: winner panel summary + opponent name badge
**Choice:** Two surfaces, both consistent across desktop and mobile.
- Winner panel: a small line `Session record: Princess <P> · Last place <L> · <R> rounds` under the existing finishing-order list, reflecting the calling user's counts. Hidden if `R == 0`.
- Opponent name badge: append `· Princess N` (when `N > 0`) and `· Last N` (when `N > 0`) inline after each opponent's name. The user's own row gets the same treatment.
**Why:** The winner panel is the natural "session check-in" moment ("how am I doing across rounds?"). The opponent badge keeps the rival-context signal alive during the next round.

### Badge uses the existing wild accent color
**Choice:** Reuse the gold/lavender accent that already marks wild ★ glyphs.
**Why:** No new palette decisions. The badge is small and inline; consistent color keeps the chip readable.

### Bots count too
**Choice:** Bot seats accumulate Princess wins and last places like humans.
**Why:** A solo player practicing against bots can read the same scoreboard. There's no privacy concern with bot scores. Treating bots specially would add edge-case branches without a payoff.

## Risks / Trade-offs

| Risk | Mitigation |
| --- | --- |
| Double-counting a game-over from re-broadcasts | The `_scoreboard_round_id` (or equivalent monotonic counter / boolean flag cleared on `start_game`) guarantees one bump per round. |
| Scoreboard drift after a converted-to-bot seat leaves | `convert_to_bot` keeps the pid, so the entry follows the seat. A subsequent `/leave` drops the entry as designed. |
| Display clutter for new players (0/0/0 everywhere) | Badges are only rendered when `> 0`. Winner-panel line is hidden when `rounds_played == 0`. |
| 3- or 4-player chips get crowded with two badges | Both UIs already truncate long names visually; badges stay inline and the existing opponent chip width handles it. |
| Spec sprawl: the same change touches three capabilities | Each capability gets exactly one new requirement (room-server) or one modified requirement (web/mobile-frontend). The cross-cutting nature is the cost of a feature that surfaces a piece of state across both UIs. |

## Migration Plan

1. `princess/rooms.py`: add `Room.scoreboard: dict[str, dict[str, int]] = field(default_factory=dict)` and `_scoreboard_round_id: int | None = None` (or boolean flag). Add `_ensure_scoreboard_entry(pid)` called from every seat-add path. Add `_drop_scoreboard_entry(pid)` called from `/remove_bot` and `/leave`. Add `_bump_scoreboard_if_needed()` that checks `game.game_over` and bumps idempotently. Update `public_lobby()` to include `scoreboard`. Update `broadcast_state()` to compute the bump (before sending) and to attach `scoreboard` to the outgoing envelope.
2. `princess/server.py`: in `/abort`, zero every entry in `room.scoreboard` (do NOT drop entries). In `/remove_bot` and `/leave` (non-convert), drop the removed pid's entry.
3. `static/app.js`, `static/styles.css`: render `· Princess N` and `· Last N` badges in the opponent row + user's own row; add the "Session record" line to the winner panel.
4. `static/mobile.js`, `static/mobile.css`: same as above with mobile-sized typography.
5. `CHANGELOG.md` `### Added` bullet.
6. Manual smoke: create a room with 2 bots, play 3 rounds with rematches, verify counts persist; click `/abort`, verify counts reset.

Rollback: revert the modified files. No data migration; in-memory state has no on-disk footprint.

## Open Questions

- Should rounds_played be displayed alongside the badges on the chip, or only in the winner panel summary line? **Decision:** winner panel only — keeps chips tight.
- Should we expose a `GET /api/rooms/{code}/scoreboard` for non-WS readers? **Decision:** no — the WS broadcast covers every seated player and there's no spectator API.
