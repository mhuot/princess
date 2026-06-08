## Context

The engine requires ≥ 2 players. The server's `POST /start` returns 409 ("need at least 2 players") if there's only the host seated. The frontend currently sends the request and surfaces a short error string. That's a poor first impression: the host just created the room, they're staring at their own seat, and the obvious next click — **Start game** — fails.

The right place to handle this is the frontend. The host's intent ("start the round") is clear; the only missing input is "how many bots." Asking that question is cheap and friendly.

## Goals / Non-Goals

**Goals:**
- Intercept the solo-start case in both UIs and offer a one-tap path to playable state.
- Stay out of the way when the room already has ≥ 2 seats — no prompt, no extra clicks.
- Reuse the existing modal patterns (centered `<dialog>` on desktop, bottom sheet on mobile).

**Non-Goals:**
- Touching the server. The 409 stays as the canonical "you sent /start with one seat" response for API consumers.
- Adding configuration for "how many bots by default." Three options (1, 2, 3) is enough for v1.
- Auto-starting without a prompt. The host must opt in.
- Pre-populating bots on room create. Many hosts want to wait for friends.

## Decisions

### Guard the click handler, not `startGame`
**Choice:** Wrap the **Start game** button's click handler (or `startGame()`) with a check on the latest `room.seats.length`. If `=== 1`, open the modal; the modal's "Add N bots" buttons handle the POST chain.
**Why:** Keeps the guard at the user-intent edge (button click), not deep in the network helper.

### Sequential `POST /bot` then `POST /start`
**Choice:** For "Add 2 bots", await two `POST /bot` calls in sequence, then await `POST /start`.
**Why:** Each `POST /bot` returns the new bot's name and broadcasts the lobby. Sequencing avoids races where two bots might collide on name selection (the server already avoids duplicates per room, but sequencing makes the UI feel deterministic — each bot appears before the next is requested).
**Trade-off:** ~200ms of round-trip per bot. With 3 bots that's <1s. Acceptable.

### Show error and cancel auto-start on any failure
**Choice:** If any `POST /bot` call fails (e.g., room full), surface the error in the lobby's existing error slot and do NOT attempt `POST /start`. The room is in a partial state (1 or 2 bots added); the host can decide whether to add more, remove, or just click **Start** again.
**Why:** Don't silently soldier on after an API failure; the host needs the truth.

### Mobile uses bottom sheet, desktop uses centered dialog
**Choice:** Match existing patterns. Mobile already has `.m-sheet` for Quit / Rules / Rename. Desktop already has centered modals.
**Why:** Visual consistency within each UI.

### Three button options: 1, 2, 3 bots
**Choice:** Buttons are **Add 1 bot**, **Add 2 bots**, **Add 3 bots**. Not a slider, not a number input.
**Why:** Tap targets are large; no parsing. Three options cover 2/3/4-player tables. The engine's max is 4 today, so a fourth button isn't needed.

### Cancel returns to the lobby in its original state
**Choice:** Cancel closes the modal/sheet with no side effects.
**Why:** Predictable. The host may have just realized they want to wait for a friend; they shouldn't pay an "Add bot" penalty for cancelling.

### Don't disable **Start game** while the modal is open
**Choice:** The button stays normally enabled. Opening the modal is a one-shot.
**Why:** Simpler state; the modal traps focus.

## Risks / Trade-offs

| Risk | Mitigation |
| --- | --- |
| Host expects the modal even with bots already in the room | The 2-seat threshold is "you're alone." If the host has already added a bot and wants more, they use **Add bot** as today. |
| Race where seat count changes between the guard read and the click | If by then `seats.length >= 2`, the guard falls through and `/start` runs. If it has dropped to 1, the modal re-opens — which is what the host expects. |
| Sequential bot adds feel slow | 3 bots × ~150ms < 0.5s. If it bothers a user, parallelize in a follow-up. |
| Cancel modal click handler conflicts with other dialog close paths | Use the `<dialog>` element's native close events; cancel does nothing on `close`. |
| Mobile sheet appears at the same time as a stale lobby error | Clear the lobby error slot when the sheet opens. |

## Migration Plan

1. Desktop: add `<dialog id="solo-start-modal">` to `index.html`; wire `startGame` click to check seat count and open the modal; modal's "Add N bots" buttons call a new `async function addBotsThenStart(n)`.
2. Mobile: add `<dialog id="m-solo-sheet" class="m-sheet">` to `mobile.html`; same guard + sheet pattern in `mobile.js`.
3. Manual smoke: create a room, click **Start** as the only seat; confirm the prompt appears with three options + cancel. Click **Add 2 bots**; confirm two bots appear in the lobby briefly, then the round starts. Then test the >1-seat path (no prompt). Mobile too.
4. `CHANGELOG.md` `## [Unreleased]` bullet.
5. Commit + push + CI + merge.

Rollback: revert the four static files. No server, no schema implications.

## Open Questions

- Should the modal also offer **Add 1 bot then wait** (i.e., don't auto-start)? Recommendation: not in v1. The host can always click **Add bot** and not press **Start**. The modal exists for the "let's just play" path.
