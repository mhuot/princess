## Context

`share-room-link` shipped a `flashShared()` helper that does:

```js
function flashShared() {
  const el = $("m-lobby-error");
  if (!el) return;
  const prev = el.textContent;
  el.textContent = "Link copied!";
  el.hidden = false;
  setTimeout(() => { el.hidden = true; el.textContent = prev; }, 1500);
}
```

`#m-lobby-error` is a `<p class="m-error" role="alert">` *inside* `#m-landing` (the pre-room landing view). The mobile UI has two top-level lobby states:
- `#m-landing` — name + create/join inputs, error slot. Visible before joining.
- `#m-room` — seat list, host controls, share button. Visible after joining.

When the user creates a room, the JS hides `#m-landing` and shows `#m-room`. The error slot's parent is now `display: none` (enforced by the `[hidden]` CSS override block). `flashShared()` flips the slot's own `hidden` attribute, but the inherited `display: none` from its parent still hides it. **The toast is invisible from the moment the share button becomes reachable.** 100% bug rate.

## Goals / Non-Goals

**Goals:**
- Restore the user feedback when the clipboard-fallback path runs.
- Stay consistent with the desktop pattern (button text → "Copied!" → original).
- Zero changes to layout, sizing, or DOM.

**Non-Goals:**
- A reusable toast/notification system. v1 is fine flashing the button.
- Animating the flash beyond a textContent swap.
- Showing the flash when `navigator.share` succeeds — the OS sheet is its own confirmation.

## Decisions

### Flash the button, not a separate element
**Choice:** Replace the button's `textContent` from `↗` to `✓` for 1500ms, then revert.
**Why:** The button is exactly where the user just tapped; their eyes are already there. No new DOM, no positioning math, can't be hidden by a parent.

### Pass the clicked button's id into the helper
**Choice:** `shareRoomLink(buttonId)`. Wire each listener with `shareRoomLink("m-share-btn-lobby")` / `shareRoomLink("m-share-btn-game")`.
**Why:** Avoids `event.currentTarget` (which depends on how the listener was added) and keeps the helper independently callable from anywhere.

### Restore the original glyph, not a hard-coded `↗`
**Choice:** Cache `prev = btn.textContent` before swapping, restore on timeout.
**Why:** If the icon glyph ever changes (font tweak, accessibility update), we don't need to update the helper.

### No flash when `navigator.share` succeeds
**Choice:** The OS share sheet is itself the confirmation; we don't flash the button after.
**Why:** Avoid a double-confirmation that's visually noisy. Matches desktop logic (`navigator.share` returns → return early).

## Risks / Trade-offs

| Risk | Mitigation |
| --- | --- |
| Button text `✓` could be misread as a checkbox glyph | Time-bound (1.5s) and the user explicitly tapped Share immediately prior — context anchors meaning. |
| Multiple rapid taps cause `prev` text to land as `✓` | Guard by setting a flag on the button while flashing: skip if already flashing. Or accept — the next tap just resets the timeout. |
| Screen readers might announce `✓` confusingly | The button's `aria-label="Share room link"` is unchanged; SR reads the label, not the icon. No regression. |

## Migration Plan

1. `static/mobile.js`: delete `flashShared()`, add `flashShareButton(buttonId)`, change `shareRoomLink` signature to take `buttonId`.
2. Wire button listeners with the corresponding button id.
3. `CHANGELOG.md` `### Fixed` bullet.
4. Commit + push + CI + merge.
5. Re-run the smoke test; confirm 16/16.

Rollback: revert the JS file.

## Open Questions

- Should we also flash the desktop button to `✓` for consistency instead of "Copied!"? Recommendation: leave desktop as **Copied!** — explicit beats clever, and the desktop has more horizontal room for full words.
