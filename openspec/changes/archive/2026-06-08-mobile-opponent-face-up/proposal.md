## Why

Face-up cards are *literally face-up on the table*. They're public information — both opponents can see them at any time. The desktop UI shows them. The mobile UI doesn't. That's an unintentional asymmetry: a mobile player walks into the same round with less visible state and loses strategic parity.

The engine already serializes the full face-up card list for every opponent (`view.players[i].face_up: [{rank, suit, label}, ...]`). The mobile `renderOpponents()` reads only `hand_count` and `face_down_count` and ignores `face_up` entirely. The fix is in the render path; no backend change.

## What Changes

- **Mobile opponent chip renders the face-up cards inline.** A small mini-card row sits below the opponent's name + turn indicator and above the existing `hand · down` counts.
- **Wild-rank ★ glyph carries over.** A face-up card whose rank is 2, 10, or the configured reverse rank gets the same `★` corner badge as wilds in the user's own hand.
- **Finished players' face-up cards visibly dim** along with the rest of the chip — they're decorative, not actionable.
- **Chip widens** from ~110px to ~180px so three small face-up cards fit comfortably alongside the name + counts. The opponent strip is already horizontally scrollable, so additional opponents (3, 4 seats) remain reachable by swipe.
- **Spec update:** the `mobile-frontend` "Game view layout (mobile)" requirement's opponents-strip clause adds the face-up cards. One new scenario per signal.

## Capabilities

### Modified Capabilities

- `mobile-frontend`: opponents strip now renders the face-up cards alongside name and counts, with wild ★ on the configured wild ranks.

### New Capabilities

(none)

## Impact

- **Affected code:**
  - `static/mobile.js` — `renderOpponents(view)` builds an opp-face-up row from `p.face_up` and appends it to the chip. The hand/down line stays.
  - `static/mobile.css` — new `.m-opp-face-up { display: flex; gap: 3px; }` and `.m-opp-mini-card` (compact ~22 × 32px). Chip's `.m-opponent { min-width: 110px → 170px; }`. The `★` glyph reuses the existing `.m-mini-card.special::after` pattern (or a scoped equivalent).
  - `static/mobile.html` — no markup change (cards rendered into the existing `.m-opponent` chip).
- **Affected APIs:** none — engine already sends `face_up`.
- **Affected dependencies:** none.
- **Docs touched:** `CHANGELOG.md` `## [Unreleased]` `### Changed` bullet.
- **Out of scope:**
  - Showing opponents' hand cards (those are private; the count is correct).
  - Tap-to-zoom on an opponent chip for a bigger view (v2 polish).
  - Animating new face-up reveals when a player plays from face-up source.
  - Changing the desktop UI (already renders them).
