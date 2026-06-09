# Smoke test report

_Generated 2026-06-09 01:43:12 UTC_  
_Tool: Playwright (Chromium headless)_  
_Base URL: https://princess.geekpark.com_

**Result: 39/39 checks passed.**

## mobile-ua-redirect (9/9)

### ✅ Mobile UA hitting / lands on /m

> url='https://princess.geekpark.com/m' title='Princess — mobile'

![Mobile UA hitting / lands on /m](screens/redirect-mobile-to-m.png)

### ✅ Mobile UA hitting /room/AB12 lands on /m/AB12

> url='https://princess.geekpark.com/m/AB12'

### ✅ Desktop UA hitting / stays on /

> url='https://princess.geekpark.com/' title='Princess Card Game'

![Desktop UA hitting / stays on /](screens/redirect-desktop-stays.png)

### ✅ ?desktop=1 keeps mobile UA on the desktop UI

> url='https://princess.geekpark.com/?desktop=1' title='Princess Card Game'

![?desktop=1 keeps mobile UA on the desktop UI](screens/redirect-desktop-query-override.png)

### ✅ Mobile lobby has 'View desktop site' link

> #m-switch-to-desktop visible=True

![Mobile lobby has 'View desktop site' link](screens/redirect-mobile-link-to-desktop.png)

### ✅ Tapping 'View desktop site' sets cookie + lands on /

> cookie='1' url='https://princess.geekpark.com/' title='Princess Card Game'

### ✅ Cookie keeps mobile UA on / on subsequent visits

> url='https://princess.geekpark.com/' title='Princess Card Game'

### ✅ Desktop footer has 'Mobile site' link

> #switch-to-mobile visible=True

### ✅ Tapping 'Mobile site' clears cookie + lands on /m

> cookie_cleared=True url='https://princess.geekpark.com/m' title='Princess — mobile' cookies={}

## deep-link-auto-join (8/8)

### ✅ Tier 3: focused view appears with no saved name

> focused_visible=True landing_hidden=True btn='Join room 59L1'

![Tier 3: focused view appears with no saved name](screens/auto-join-focused-view.png)

### ✅ Join button disabled on empty input

> button.disabled=True

### ✅ Whitespace-only input keeps button disabled

> button.disabled=True

### ✅ Non-empty input enables the button

> button.disabled=False

### ✅ Tier 3 submit trims and saves name; enters room

> saved_name='Pat' room_visible=True

### ✅ Tier 2: saved name auto-joins without focused view

> landed_in_room=True focused_shown=False

![Tier 2: saved name auto-joins without focused view](screens/auto-join-tier2-saved-name.png)

### ✅ Session sentinel persisted after join

> sentinel='{"code":"59L1","pid":"YHN57ZRhqNc","name":"Mike"}'

### ✅ Failure (404) falls back to landing with code prefilled + error

> landing_back=True code_input='ZZZZ' error_visible=True

![Failure (404) falls back to landing with code prefilled + error](screens/auto-join-failure-fallback.png)

## sentinel-reject-soft-fallback (3/3)

### ✅ Stale sentinel + room gone + saved name: no reload, landing visible

> nav_before=1 nav_after=1 landing_visible=True error_visible=True

### ✅ Stale sentinel + room exists + saved name: no reload, user seated

> seated=True nav_before=1 nav_after=1

### ✅ Stale sentinel + room exists + no saved name: focused view, no reload

> focused=True nav_before=1 nav_after=1

## websocket-reconnect (2/2)

### ✅ Mid-session close: banner shows Reconnecting… and actions disabled

> banner_text='Reconnecting…' play_disabled=True pickup_disabled=True

### ✅ Successful reopen: banner returns to live (hidden) state

> Banner auto-hides after Reconnected flash.

## share-room-link (7/7)

### ✅ Desktop lobby shows Share link button

> Room FSEO

![Desktop lobby shows Share link button](screens/share-desktop-lobby.png)

### ✅ Desktop Share button flashes 'Copied!'

> Label after click: 'Copied!'

![Desktop Share button flashes 'Copied!'](screens/share-desktop-copied.png)

### ✅ Desktop clipboard URL matches /room/<code>

> clipboard='https://princess.geekpark.com/room/FSEO' expected='https://princess.geekpark.com/room/FSEO'

### ✅ Mobile lobby shows ↗ share button

> Room M2BS

![Mobile lobby shows ↗ share button](screens/share-mobile-lobby.png)

### ✅ Mobile share button glyph flashes to ✓

> button text mid-flash='✓' (expected '✓')

![Mobile share button glyph flashes to ✓](screens/share-mobile-flash.png)

### ✅ Mobile share button glyph reverts after flash

> button text after flash='↗' (expected '↗')

### ✅ Mobile clipboard URL matches /m/<code>

> clipboard='https://princess.geekpark.com/m/M2BS' expected='https://princess.geekpark.com/m/M2BS'

## mobile-discard-count (4/4)

### ✅ Created mobile room

> Room I6D0

### ✅ Setup phase visible (Discard count won't render here, but pile-area UI not yet)

> deck='' discard=''

![Setup phase visible (Discard count won't render here, but pile-area UI not yet)](screens/discard-setup-phase.png)

### ✅ Playing phase shows Deck and Discard stats

> deck='24' discard='1'

![Playing phase shows Deck and Discard stats](screens/discard-playing-phase.png)

### ✅ Discard rendered below Deck in same column

> deck_y=271.234375 discard_y=320.171875

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
