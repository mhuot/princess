## Context

`view.players[i].face_up` is an array of `{rank, suit, label}` for every player including opponents. The engine has always sent it. Desktop renders it as a mini-card row inside the opponent's box. Mobile's `renderOpponents()` was written for the original ultra-compact strip layout (room for ~3 chips on a 390px screen) and skipped the cards to keep the chip tiny.

Now that the player base is using mobile for full sessions (not just spectating), strategic parity with desktop matters. The face-up cards are part of the table state; hiding them is a UX regression relative to the physical card game and to the desktop sibling.

## Goals / Non-Goals

**Goals:**
- Surface every opponent's face-up cards on mobile, in the same chip as their name and counts.
- Mark wild ranks (2 / 10 / configured reverse rank) on opponent face-up cards with the same ★ glyph used for the player's own wilds.
- Keep the strip horizontally scrollable so 3- and 4-player rooms still work at 390px.
- Match desktop's information density on opponents without breaking mobile's "compact chip" feel entirely.

**Non-Goals:**
- Showing hand cards. Those stay private; only `hand_count` is sent.
- Tap-to-zoom on opponent chips. Useful but separate change.
- Animating face-up changes (card highlights on play, reveal flips). Polish for later.
- Changing the desktop UI. It already shows them.
- Reordering / sorting opponent face-up cards. Render them in `p.face_up` array order.

## Decisions

### Inline, not tap-to-expand
**Choice:** Render the face-up cards directly in the chip.
**Why:** Face-up cards are public information. Adding a tap to see public info is friction without benefit. The desktop UI doesn't gate them behind a tap; mobile shouldn't either.

### Chip widens from ~110px to ~170px
**Choice:** Bump the chip width so 3 mini cards (about 22 × 32 px each + 3 px gap) fit alongside the existing `hand · down` line and the name.
**Why:** Three face-up cards is the max engine-side; the chip can accommodate them at a comfortable size without breaking the horizontal-scroll affordance. ~2 chips fully visible at 390 px; rest by swipe.

### Mini-card size: ~22 × 32 px
**Choice:** A bit smaller than the player's own face-up mini cards (~32 × 46 px) but readable. Rank + suit char rendered with font-size ~0.65 rem.
**Why:** Optimizes for "I can see at a glance which wilds they have." Anyone wanting a closer look has the desktop UI.

### Wild ★ glyph on opponent face-up cards
**Choice:** A face-up card whose rank is `2`, `10`, or `view.config.reverse_rank` gets a top-right `★`, same glyph the player's own hand uses.
**Why:** The whole point of seeing opponent face-up is strategic. "Bob has a 10 on the table" is the most important signal.

### Show below the name, above the counts
**Choice:** Vertical order within the chip:
  1. Name + (bot) tag
  2. Turn dot if it's their turn / finished tag
  3. **Face-up row** (this change)
  4. `hand N · down N` counts
**Why:** Cards are visual; show them prominently. Counts read as metadata below.

### Empty / zero face-up rendered as empty space, not "—"
**Choice:** If `face_up.length === 0`, render the row empty (height collapses).
**Why:** A player can deplete their face-up over the round. Rendering "—" makes the chip taller than its neighbors and creates a jagged strip.

### Finished player chips dim everything together
**Choice:** Existing `.finished` class already sets `opacity: 0.55` on the chip; the face-up cards inherit. No special-case.
**Why:** Once they're out of the round, all their state is decorative.

### Render in `face_up` array order
**Choice:** Don't sort. The engine sends cards in the order the player locked them in at setup; that ordering is meaningful to the player.
**Why:** Sorting would mask information ("which one did they pick first?") for no gain.

## Risks / Trade-offs

| Risk | Mitigation |
| --- | --- |
| 4-seat room becomes hard to scan with wider chips | Strip is horizontal-scrollable; player can swipe. We accept fewer chips visible at once as the cost of more info per chip. |
| ★ glyph visually competes with the rank/suit text on tiny 22×32 cards | Glyph is 0.55 rem at top-right; tested at 22×32 it's readable without overlapping the rank in the center. |
| Network broadcast cost grows minimally (already serializing face-up) | No change — engine has always sent the cards. Mobile was discarding them. |
| Desktop and mobile drift apart on opponent rendering | Both UIs now surface face-up cards. Future renders should keep this parity in mind; documented in the spec. |

## Migration Plan

1. `static/mobile.js`: extend `renderOpponents(view)` to build a `<div class="m-opp-face-up">` containing one `<span class="m-opp-mini-card">` per card in `p.face_up`. Apply `.special` class when the card's rank is wild.
2. `static/mobile.css`: bump `.m-opponent { min-width: 170px; }`. Add `.m-opp-face-up { display: flex; gap: 3px; margin: 4px 0 2px; }` and `.m-opp-mini-card` (~22 × 32 px, same color palette as `.m-mini-card`, with the wild `::after` star).
3. `CHANGELOG.md` `### Changed` bullet.
4. Manual smoke at 390 × 844.
5. Commit + push + CI + merge.

Rollback: revert the two static files. Engine + server + desktop untouched.

## Open Questions

- Could we show face-down counts as small back-card icons rather than `· down 3`? Maybe in a follow-up; for v1 the text count is fine.
