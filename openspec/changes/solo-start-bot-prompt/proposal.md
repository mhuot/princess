## Why

Today, when the host clicks **Start game** in a room with only themselves seated, the server rejects with "need at least 2 players" and the lobby shows a bare error message. The host then has to find **Add bot** themselves. It's a small frustration, but it's the very first interaction someone has after creating a room — for many solo players it's the *entire* first session.

Catch the case in the UI: when **Start** is clicked with one seat, intercept and ask "You're alone in the room. Add a couple of bots so the round can start?" with one-tap options to add 1, 2, or 3 bots. Confirm → add bots → start. Cancel → return to the lobby. Both UIs (desktop and mobile) get the prompt.

## What Changes

- **Frontend behavior (desktop and mobile):** before the host's **Start game** click POSTs `/start`, check `room.seats.length`. If exactly 1 (i.e., only the host), open a modal:
  - Title: "You're alone in the room."
  - Body: "Add some bots and we'll start the round right after."
  - Three primary buttons: **Add 1 bot**, **Add 2 bots**, **Add 3 bots**.
  - A secondary **Back to lobby** button (closes the modal; no API calls; the host stays on the lobby they came from).
  - On primary click: POST `/api/rooms/{code}/bot` the chosen number of times (sequentially — each call returns a name; we wait for each to land so the seat list reflects reality), then POST `/start`.
- **Desktop UI:** the modal uses a centered `<dialog>` (matches the existing Quit modal pattern).
- **Mobile UI:** the modal uses a bottom sheet (matches the existing Quit / Rules / Rename pattern).
- **Server behavior unchanged.** The existing "need at least 2 players" rejection stays as a backstop for direct API users. The frontend just avoids ever triggering it.
- **Edge cases:**
  - If the host already has 1+ humans **or** 1+ bots beyond themselves (i.e., `seats.length >= 2`), **no prompt**. Start as today.
  - If the room is at the seat cap and the user requests more than fits, only add up to the cap and then start. (Defensive — current cap is high enough that 3 bots always fit, but we don't crash if that changes.)
  - If any **Add bot** call fails (room full, server error), surface a short error and abort the auto-start; the lobby remains as-is.

## Capabilities

### Modified Capabilities

- `web-frontend`: lobby's **Start game** click intercepts solo state and prompts; reuses the existing centered-dialog pattern.
- `mobile-frontend`: lobby's **Start game** intercepts solo state and prompts via a bottom sheet; reuses the existing sheet pattern.

### New Capabilities

(none)

## Impact

- **Affected code:**
  - `static/app.js` — wrap the existing `startGame` (or its click handler) with a guard; new `solo-start-sheet` open/close logic; helpers `addBots(n)` that loops `POST /bot` and resolves once done.
  - `static/index.html` — add a `<dialog id="solo-start-modal">` (matches `#quit-modal` styling).
  - `static/styles.css` — minor styling (reuse `.quit-modal-*` patterns).
  - `static/mobile.js` — same guard in the mobile lobby's start handler; reuses the `.m-sheet` `<dialog>` pattern.
  - `static/mobile.html` — add `<dialog id="m-solo-sheet" class="m-sheet">`.
  - `static/mobile.css` — no new rules; the existing `.m-sheet` covers it.
- **Affected APIs:** none. Backend unchanged.
- **Docs touched:**
  - `CHANGELOG.md` `## [Unreleased]` `### Changed` (or `### Added`) bullet.
- **Depends on:** none beyond main.
- **Out of scope:**
  - Auto-starting after adding bots without a prompt (silent magic).
  - Server-side auto-fill ("if 1 seat at /start, server adds bots"). The prompt approach keeps the host in control.
  - Letting non-hosts add bots from the prompt (they can't add bots today either).
  - Customizing the **bot count options** (Add 1 / 2 / 3) per host preference.
