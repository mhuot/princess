## Why

A room can currently end up with two seats named the same thing — two humans joining as **Mike**, a human renaming to a bot's name, etc. Once that happens, every downstream reference to a player by name becomes ambiguous:

- Status entries like `"Mike played 8♠ — Your turn"` — *which* Mike?
- Opponent strip chips both labeled `Mike (bot)` and `Mike` — indistinguishable at a glance.
- Winner panel saying `Mike won the round!` — congratulations to one of you?
- The `last_actions` history baked into rematches still references "Mike" with no way to tell the rounds apart.

`pick_bot_name(taken)` already keeps bot names unique inside the same room. The gap is on the human side — `/api/rooms/<code>/join` and `/api/rooms/<code>/rename` accept any name without checking the existing seats. Close the gap.

## What Changes

- **Server-side uniqueness check** added to three endpoints:
  - `POST /api/rooms` (room creation) — the host's chosen name has no peers yet, so this is always fine. Trim the input here too for consistency.
  - `POST /api/rooms/<code>/join` — reject with **409 Conflict** if any existing seat has the same name.
  - `POST /api/rooms/<code>/rename` — reject with **409** if any *other* seat has the new name. The caller renaming to their own current name is a no-op (still 200, no broadcast).
- **Comparison is case-insensitive + whitespace-trimmed.** `"Mike"`, `"mike"`, and `"  MIKE  "` all collide. The stored name keeps the original casing the user provided.
- **Errors are user-readable.** The 409 detail is `"name 'Mike' is already taken in this room"` so the desktop / mobile UIs can surface it verbatim.
- **Client handling:**
  - Desktop: the existing `showError("lobby-error", e.message)` and the deep-link auto-join failure path already render the message; no new UI is needed.
  - Mobile: same — `showError(e.message)` covers it.
  - Rename flows: the existing inline-rename (desktop) and rename-sheet (mobile) handlers receive the error and surface it via `showError`. For v1 the desktop inline input is already torn down before submit; the user just clicks **Rename** again with a different name. (A nicer "keep the input open on error" tweak is a small follow-up.)
- **Tests:** server tests cover the join-dupe, rename-dupe, rename-self (no-op), case-insensitive collision, and whitespace-trimmed collision cases.

## Capabilities

### Modified Capabilities

- `room-server`: `/api/rooms`, `/join`, and `/rename` enforce per-room unique names (case-insensitive, whitespace-trimmed).
- `web-frontend`: surface the new 409 via the existing error slots.
- `mobile-frontend`: surface the new 409 via the existing error helper.

### New Capabilities

(none)

## Impact

- **Affected code:**
  - `princess/server.py`:
    - New helper `_name_already_taken(room, name, *, exclude_pid: str | None = None) -> bool` that does case-insensitive + whitespace-trimmed comparison against `seat.name` for every seat (humans + bots), optionally excluding one pid (the caller's own seat for rename).
    - `create_room` (`POST /api/rooms`): trim the host's name and persist the trimmed form on the seat (no dupe check needed — host is the first seat).
    - `join_room` (`POST /join`): trim the name and reject with 409 if `_name_already_taken(room, name)` is True.
    - `rename_seat` (`POST /rename`): trim the new name; if `_name_already_taken(room, new_name, exclude_pid=body.pid)` is True, reject with 409. If the trimmed new name equals the current seat's name (after trimming both), return 200 without broadcasting.
  - `tests/test_server.py`:
    - `test_join_rejects_duplicate_name`
    - `test_join_rejects_case_insensitive_duplicate`
    - `test_join_rejects_whitespace_padded_duplicate`
    - `test_join_rejects_name_matching_a_bot`
    - `test_rename_rejects_duplicate_name`
    - `test_rename_to_own_name_is_noop`
    - `test_create_room_trims_host_name`
- **Affected APIs:** `POST /join`, `POST /rename` may now return **409**. Existing clients already handle 4xx by surfacing the error message; no breaking change in shape.
- **Docs touched:** `CHANGELOG.md` `### Changed` (this is an additional constraint on existing endpoints).
- **Out of scope:**
  - Suggesting an alternative name on collision (e.g., "Mike 2"). Just reject and let the user pick.
  - A separate "stable seat id" displayed alongside the name to disambiguate. Names are the only label today; that's fine for a 2–4 player room.
  - Persisting names across sessions (already handled by `localStorage.princess_name`).
  - Tightening the rename UX so the inline input stays open on error. Worth a tiny follow-up if anyone reports friction.
