## Context

Today's `beginRenameInline` is fire-and-forget: it removes the input the moment `submit()` runs, then kicks `renameSelf(value)` which POSTs and routes any error to `#lobby-error`. The user sees the error but has no input to fix — the name span is back. They have to click **Rename** again to reopen the input.

The fix is small. The mobile sheet already shows the right pattern — keep the editor visible until the POST returns 200, surface the error if not. We're porting that pattern to the desktop and tightening one mobile rough edge (refocus + select on error).

## Goals / Non-Goals

**Goals:**
- Desktop: on rename error, the input stays visible with text selected so the user can immediately retype.
- Both: any 4xx is handled the same way (409 collision, 422 overlength).
- No new error DOM elements; reuse `#lobby-error` (desktop) and the global mobile error helper.
- Survive a slow server: input is disabled in-flight to prevent double submit.

**Non-Goals:**
- Client-side pre-validation of dedupe (server is source of truth).
- A per-row inline `.rename-error` element (the existing slot is fine).
- Auto-suggesting alternative names.
- Polishing `promptRenameForGame` (native prompt is acceptable for v1; this change is scoped to the lobby surfaces).

## Decisions

### Make `renameSelf` return a boolean, and have `beginRenameInline` await it
**Choice:** `renameSelf(newName)` returns `true` on success and `false` on any failure (the catch block already calls `showError`, so the boolean is purely a control-flow signal for the caller). `beginRenameInline.submit()` becomes async, awaits the boolean, and only tears down the input on `true`.
**Why:** Smallest possible change. The function is already async; switching the signature from `void` to `boolean` doesn't ripple to other call sites that ignore the return value.

### On failure: re-focus + select the input
**Choice:** After `renameSelf` returns false, call `input.disabled = false; input.focus(); input.select();`.
**Why:** Matches the desktop pattern for inline editors (e.g., the focused-join name view re-focuses on error). Selection means the user's next keystroke replaces the offending value with no extra clicks.

### Disable the input while the POST is in flight
**Choice:** Set `input.disabled = true` before awaiting the POST; restore on failure; on success the input is replaced and discarded.
**Why:** A user mashing Enter twice could double-submit; the server's no-op self-rename path would absorb the second, but disabling is cheap insurance. Also avoids the visual "stale value while we wait" issue if latency spikes.

### Don't introduce a `.rename-error` element
**Choice:** Surface the error in `#lobby-error` (already used by `renameSelf`'s catch via `showError("lobby-error", e.message)`).
**Why:** The error slot sits directly above the seat list; the user sees it. Adding per-row error spans is more DOM, more CSS, marginal UX gain.

### Blur during in-flight submit is a no-op
**Choice:** Once the user hits Enter, blur events are ignored until the submit resolves. The existing `settled` flag already does this; we keep it.
**Why:** Prevents a double-submit if focus shifts while the POST is in flight.

### Escape cancels even during in-flight submit
**Choice:** Escape sets a `cancelled` flag and re-renders the original name span; if the POST returns 200, the broadcast re-render handles the new name regardless. If the POST returns 4xx, the error still surfaces in `#lobby-error` but the input is gone.
**Why:** Escape is the user's "get me out of here" key; honoring it always is the right tradeoff. If they cancel and the rename actually succeeded server-side (race), the broadcast updates the row name and we're consistent.
**Alternative considered:** Block Escape during in-flight. Rejected — the round-trip is usually <50ms; locking input feels wrong.

### Mobile: refocus + select inside the catch
**Choice:** In `submitRename`, after `showError(e.message)`, call `$("m-rename-input").focus(); $("m-rename-input").select();`.
**Why:** Same one-line keystroke savings as desktop. Mobile sheet stays open today; this just makes the recovery faster.

### Mobile: no input disable during in-flight
**Choice:** Don't disable the mobile input. The sheet has a separate Submit button (`#m-rename-submit`) that we could disable, but the latency is sub-100ms and the user already has to lift and re-tap.
**Why:** Mobile interactions are slower per-tap than desktop key presses; the failure mode the disable prevents is rare on mobile. Keep the change small.

### Handle 422 and 409 identically
**Choice:** The catch block doesn't branch on status — any rejection means "keep input open, surface message, refocus, select." `postJSON` already extracts the server's `detail` into `e.message` for both 409 and 422.
**Why:** The user's correction in both cases is "change the name." No need for different UX.

## Risks / Trade-offs

| Risk | Mitigation |
| --- | --- |
| The broadcast for a successful rename arrives BEFORE the awaited POST resolves locally; the lobby re-renders, the input element gets blown away, then our success path tries to call `input.replaceWith(nameCell)` on a detached node | Detached node calls are safe no-ops; verify with manual test (two tabs). The `settled` flag prevents double tear-down regardless. |
| User cancels with Escape while a successful POST is in flight; the row briefly flashes the old name before the broadcast re-render updates it to the new name | Cosmetic; the broadcast lands within ~50ms. Acceptable. |
| Disabling the desktop input causes a focus jump | We restore focus + selection in the catch path. On success the element is removed, so focus naturally moves to the document. |
| Some browsers don't honor `input.select()` on a `disabled` input | We re-enable BEFORE selecting. |
| A consumer of `renameSelf` outside `beginRenameInline` (e.g., `promptRenameForGame`) ignores the new boolean return value | Returning `boolean` from a function that previously returned `void` is backward-compatible at the JS level (callers see `undefined → false-coerce`; new callers get the truthful value). No call-site changes needed for the prompt path. |

## Migration Plan

1. **`static/app.js`:**
   - Change `renameSelf` to return `true`/`false`.
   - Rewrite `beginRenameInline.submit` as async: set `input.disabled = true`, await `renameSelf(value)`; on `false`, set `input.disabled = false; input.focus(); input.select();`; on `true`, run `input.replaceWith(nameCell)`.
   - Keep `cancel()` (Escape) unchanged.
2. **`static/mobile.js`:** In `submitRename`'s catch, after `showError(e.message)`, call `$("m-rename-input").focus(); $("m-rename-input").select();`.
3. **CHANGELOG `[Unreleased]` `### Changed`:** one-line note.
4. **Manual smoke (two tabs):**
   - Desktop: tab A as "Mike", tab B as "Pat"; in tab B click Rename, type "Mike", Enter — expect input remains, error visible, text selected, retype "Pat2", Enter — expect success.
   - Desktop: same flow with a 21-character name — expect 422 surface and input stays open.
   - Mobile: same flow in the bottom sheet; verify the sheet stays open, the input is focused with text selected.
5. Commit + push + CI + merge.

Rollback: revert the two static files. Server is untouched.

## Open Questions

- Should we also disable the **Rename** button (the per-row trigger) while the input is open, so a user can't click it again and reset the editor? **Recommendation:** no. Clicking Rename while an input is already in place is a niche path; the existing `settled` flag protects against weird state. Keep the diff small.
- Should the success path explicitly clear `#lobby-error` (in case a prior error is still lingering)? **Recommendation:** yes — a successful rename should drop any previous error. Add `clearError("lobby-error")` at the end of the success branch. Trivial. (Tracked in `tasks.md`.)
