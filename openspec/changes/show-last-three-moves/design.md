## Context

Today `Game.last_action: str` is overwritten on every event — set during `_deal_with_swap`, `_play_face_down`, `_apply_committed_cards`, `pickup`, and the `set_face_up` ready transition. `public_state()` includes it as a plain string. The frontend reads `view.last_action`, appends a turn suffix ("— Your turn." / "— Bob's turn."), and renders it in `#status-line` with `aria-live="polite"`.

When `Room.run_bots()` advances multiple bot actions in a row (each with its own `last_action` update + state broadcast), the human sees the broadcasts arrive but each one stomps the previous string. The user wants to see all three so they can follow the sequence.

## Goals / Non-Goals

**Goals:**
- Show the last three game events on the status line, newest emphasized.
- Keep the change small enough that the engine stays trivially serializable (still a list of dicts, no event-source ledger).
- Preserve `aria-live` ergonomics so a screen reader hears the newest line once, not all three on each update.
- Cover all action paths — play, multi-card play, burn, pickup, face-down (legal + illegal), setup ready, deal-complete.

**Non-Goals:**
- A full game log / history panel. That's a future change; this lives in the same screen region as today.
- Action timestamps. The order is enough.
- Localization. Strings stay in English, as today.
- Replay or undo. The list is purely informational.

## Decisions

### Bounded list of three, newest at the end
**Choice:** `Game.last_actions: list[dict]` with a hard `len <= 3`. Always append; if `len > 3`, pop from the front. Most recent is `last_actions[-1]`.
**Why:** "Newest at the end" matches the existing single-string semantics for any code that reads "the most recent action" (it's still the last element). The list is short, so a manual cap is simpler than `collections.deque`.
**Alternatives:** Newest-at-front would invert the index but require flipping logic in the frontend. Same data, more confusion.

### List of dicts, not list of strings
**Choice:** Each entry is `{"text": str, "actor_pid": str | None, "burned": bool, "picked_up": bool, "finished_pid": str | None}`.
**Why:** The frontend wants to style burns ("🔥") and finishes ("👑") differently from plain plays. A structured entry avoids brittle string parsing on the client.
**Trade-off:** Slightly more wire bytes. Negligible.

### Single source of truth — engine writes; server doesn't post-process
**Choice:** All `last_actions` appends happen inside `Game`. The room/server only forwards `public_state()`.
**Why:** Keeps a single audit point for "did this action get recorded?" and lets the engine's unit tests cover the rendering contract.

### Legacy `last_action` key retained for one release
**Choice:** `public_state()` continues to emit `last_action` as the `.text` of the newest entry. Marked deprecated; removed in a follow-up change once we're confident no external consumers exist.
**Why:** Cheap safety net. The existing test (`test_face_down_illegal_play_picks_up_pile_plus_card` and friends) doesn't actually read `last_action`, but removing the field in the same change increases blast radius for no benefit.

### Status stack render: newest bottom, older dimmed
**Choice:** Render entries top-to-bottom as `last_actions[0..N]`, so the newest is at the bottom (closest to the player's cards). Older entries get reduced opacity. The newest still receives the turn-suffix ("— Your turn." or "— Bob's turn.").
**Why:** Eyes naturally read down toward the cards. "Last entry near the action" feels right.
**Alternatives considered:** newest-on-top (chat-style) — fine but inverts the existing visual position. Tooltip / hover-only — hides the new info; defeats the point.

### Aria-live still announces only the newest
**Choice:** Wrap the stack in a static container; only the newest line carries `aria-live="polite"`. Old lines get `aria-hidden="true"` so they're visible but not re-announced.
**Why:** Otherwise SR users get the same three lines re-announced on every state broadcast.

### Bot action storm: one append per action, broadcast as usual
**Choice:** `run_bots()` already broadcasts state after every bot action. Each broadcast appears with the updated `last_actions` (newest at the end). The 0.6s think delay between bot actions means the human will see each entry land in turn.
**Why:** No new pacing logic required. The visual cadence is "1 line appears, then 2, then 3" — a natural reveal.

## Risks / Trade-offs

| Risk | Mitigation |
| --- | --- |
| Three messages in <600ms could be visually noisy | Each entry has the actor's name, so context is preserved; the cap of three prevents pile-on. |
| Renaming `last_action` → `last_actions` breaks a hypothetical external client | Keep both keys for this release; remove the singular form in a follow-up change. |
| Older lines distract from the legality / turn cue | Dim older entries (opacity ~0.6) and reserve the high-contrast turn suffix for the newest. |
| Setup-phase deal-complete message pushes earlier setup events out | Acceptable; setup is a short, linear flow and the newest message ("game on!") is the relevant one. |
| Localization later wants pre-formatted strings, but we'd want IDs | Defer; today's strings are English and inline. Switching to translation keys is a separate change. |

## Migration Plan

1. Engine change: introduce `Game.last_actions: list[dict]`. Helper `_record(text, **flags)` appends and trims.
2. Replace every `self.last_action = "..."` with `self._record("...")` plus the relevant flags.
3. Update `public_state()` to emit `last_actions` and a fallback `last_action` (text of the newest).
4. Update existing tests that reference `game.last_action`; replace with `game.last_actions[-1]["text"]`. The legacy field also still works.
5. Frontend: rename `#status-line` to `#status-stack`, render up to three entries with newest emphasized and styled by burn/pickup/finish flags. Update `renderStatus(view)` accordingly.
6. CSS: new `.status-stack` and `.status-entry` styles.

Rollback: revert the engine change; the frontend tolerates a missing `last_actions` by falling back to `last_action` (already in the new render path).

## Open Questions

- Should the history persist across **multiple games** (rematches) — i.e., the first three lines of round 2 still show "Bob finished 2nd, last round"? Probably not — the rematch reset clears it. Confirm during implementation.
- Do we want a "history" icon that expands into a full game log later? That's a follow-on change.
