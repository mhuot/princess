## Context

The room registry holds an in-memory list of `Seat` objects with a `name` field. Today the only place that checks for duplicates is `pick_bot_name(taken)` in `bot_names.py`, which the `/bot` endpoint already invokes with `{s.name for s in room.seats}` — so bot picks already avoid collisions with humans + other bots. The two gaps are:

- `POST /join` — accepts any `name`, appends a seat regardless.
- `POST /rename` — sets `seat.name = body.new_name` unconditionally.

A duplicate seat name is purely a display problem (the engine identifies players by `pid`, not name), but display is what the player sees on every status line, opponent chip, and winner panel. So we close it at the API boundary.

## Goals / Non-Goals

**Goals:**
- Server-side enforcement: no two seats in the same room share a name.
- Case-insensitive + whitespace-trimmed comparison (`Mike` and `mike  ` collide).
- Clear 409 with a readable detail so existing client error surfaces work without UI changes.
- Bot picks still avoid all seat names (already covered by current code; verify with a test).

**Non-Goals:**
- Suggesting an alternative name ("Mike 2"). Reject and let the user retry.
- Adding a stable secondary id displayed beside the name.
- Cross-room uniqueness (sessions are room-scoped).
- A streamlined "edit-in-place on error" rename UI; the user retries.

## Decisions

### Trim and case-fold for comparison; store the original casing
**Choice:** `_name_already_taken` compares `seat.name.strip().casefold() == new_name.strip().casefold()`. The seat's stored `name` keeps whatever casing the user typed (after trimming).
**Why:** `Mike` and `mike` mean the same person to a reader, so they should collide. But the user who typed `MIKE` should see their seat as `MIKE`, not be silently lowercased.

### Trim incoming names everywhere they're persisted
**Choice:** Strip whitespace before storing — `create_room`, `join_room`, `rename_seat` all `.strip()` the name before assignment. Pydantic already enforces 1–20 char bounds; trimming runs before that check would otherwise fail on `" "` which the bound treats as length-1.
**Why:** `"  Mike  "` and `"Mike"` are the same name; storing the trimmed form keeps display clean.

### Reject with **409 Conflict**, not 422 / 400
**Choice:** 409 is for "the request conflicts with current state" — perfect fit for "another seat already has this name."
**Why:** 422 is for syntactic / schema validation; 400 is the catch-all. 409 specifically means "your request is fine on its own, but state forbids it."

### Detail message: `"name 'Mike' is already taken in this room"`
**Choice:** Quote the offending name in single quotes so it's obvious in the client error toast.
**Why:** "Name already taken" without the name is ambiguous when a user has tried two variants.

### Self-rename to own current name is a no-op, not an error
**Choice:** If `rename_seat` is called with `new_name.strip().casefold() == seat.name.strip().casefold()`, return 200 without changing anything and without broadcasting.
**Why:** A user typing their existing name shouldn't see an error. Skipping the broadcast also avoids needless WS traffic.

### Exclude the caller's pid from the dedupe check on rename
**Choice:** `_name_already_taken(room, name, exclude_pid=body.pid)` — the rename's "other seats" set is all seats minus the caller's own.
**Why:** Without exclusion, you couldn't rename to a slight variation of your own name. With it, only conflicts with *other* seats matter.

### Don't pre-validate on the client
**Choice:** No client-side check that fires before the API call. Submit, let the server reply 409, surface the error.
**Why:** The room's seat list lives on the server. The client's snapshot can lag. Server is the single source of truth, and the round-trip is cheap.

### Bot-name picking remains unchanged
**Choice:** `pick_bot_name(taken)` already considers all seats. Just verify with a test that adding a human named "Galaxy Brain" doesn't let a bot also become "Galaxy Brain."
**Why:** Defensive; no code change required.

## Risks / Trade-offs

| Risk | Mitigation |
| --- | --- |
| A user who frequently types whitespace into their name sees a name that's been silently trimmed | The trim is visible (their stored name on the seat row reflects it), so they can rename if they object. |
| Case-insensitive collision feels surprising ("but my Mike is uppercase!") | Error message includes the existing name so they can see the case difference. |
| A user keeps retrying the same name and burning round-trips | Each round-trip is <50ms locally; pathological case is not worth client-side throttling. |
| Renaming UX is awkward because the inline input is gone before the error returns (existing bug, not introduced here) | Out of scope; can be tightened in a follow-up. Error still surfaces via the existing error slot. |
| Tests don't cover an i18n edge ("ß" vs "SS" casefold) | We use Python's `str.casefold()` which handles Unicode correctly. No special-case tests needed for v1; revisit if a user reports something. |

## Migration Plan

1. **`princess/server.py`:** add `_name_already_taken` helper. Wire it into `join_room` and `rename_seat`. Trim all incoming names before persistence.
2. **Tests:** add the seven cases listed in the proposal.
3. `black princess tests`, `pylint princess tests`, `pytest -q`, `openspec validate ... --strict`.
4. **CHANGELOG `### Changed`** entry.
5. Commit + push + CI + merge.

Rollback: revert `server.py` and the test additions. No client or schema changes.

## Open Questions

- Should the 409 also fire from the create-room endpoint when the host's name matches an existing bot's reserved name from the 100-bot list? **Recommendation:** no. Bots in a room are dynamic; the bot-name list is just a pool. A human picking "Galaxy Brain" only matters if a bot named that is *already in this room*, in which case the bot was added before the human joined, and the human is hitting `/join` (which IS checked). Cleanly scoped.
- Should we surface a hint like "Names are case-insensitive" on the focused-join view? **Recommendation:** no — would clutter a single-input panel. The error message is enough on collision.
