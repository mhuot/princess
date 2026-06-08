# Smoke test report

_Generated 2026-06-08 21:04:29 UTC_  
_Tool: Playwright (Chromium headless)_  
_Base URL: http://127.0.0.1:8000_

**Result: 17/17 checks passed.**

## share-room-link (7/7)

### ✅ Desktop lobby shows Share link button

> Room 8DZB

![Desktop lobby shows Share link button](screens/share-desktop-lobby.png)

### ✅ Desktop Share button flashes 'Copied!'

> Label after click: 'Copied!'

![Desktop Share button flashes 'Copied!'](screens/share-desktop-copied.png)

### ✅ Desktop clipboard URL matches /room/<code>

> clipboard='http://127.0.0.1:8000/room/8DZB' expected='http://127.0.0.1:8000/room/8DZB'

### ✅ Mobile lobby shows ↗ share button

> Room CUR5

![Mobile lobby shows ↗ share button](screens/share-mobile-lobby.png)

### ✅ Mobile share button glyph flashes to ✓

> button text mid-flash='✓' (expected '✓')

![Mobile share button glyph flashes to ✓](screens/share-mobile-flash.png)

### ✅ Mobile share button glyph reverts after flash

> button text after flash='↗' (expected '↗')

### ✅ Mobile clipboard URL matches /m/<code>

> clipboard='http://127.0.0.1:8000/m/CUR5' expected='http://127.0.0.1:8000/m/CUR5'

## mobile-discard-count (4/4)

### ✅ Created mobile room

> Room EB68

### ✅ Setup phase visible (Discard count won't render here, but pile-area UI not yet)

> deck='' discard=''

![Setup phase visible (Discard count won't render here, but pile-area UI not yet)](screens/discard-setup-phase.png)

### ✅ Playing phase shows Deck and Discard stats

> deck='24' discard='1'

![Playing phase shows Deck and Discard stats](screens/discard-playing-phase.png)

### ✅ Discard rendered below Deck in same column

> deck_y=291.390625 discard_y=340.328125

## mobile-hand-scroll-hint (4/4)

### ✅ Scroll hint chip element exists in DOM

> count=1 hidden_for_small_hand=True

### ✅ #m-game reserves bottom padding for the action bar

> computed padding-bottom=76px (need >= 50px)

### ✅ Hand sentinel attached at end of hand row

> sentinel count=1

### ✅ Chip stays hidden when the whole hand fits

> Small starting hand; nothing to overflow.

![Chip stays hidden when the whole hand fits](screens/scroll-hint-small-hand.png)

## supporting visuals (2/2)

### ✅ Opponent face-up cards rendered in chip

> m-opp-mini-card count=6

![Opponent face-up cards rendered in chip](screens/mobile-playing-overview.png)

### ✅ Hand rendered as wrap row

> hand card count=3
