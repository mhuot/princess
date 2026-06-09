## ADDED Requirements

### Requirement: Play & burn animations (mobile)

The mobile frontend SHALL fire the same four CSS-keyframe animations as the desktop UI in response to flagged entries appearing in `view.last_actions`, scoped to the mobile DOM (`#m-pile-card`, `#m-pile`, `#m-hand-row`, `#m-winner-name`). Animations are triggered by JS class-toggling against existing mobile elements; all timing and easing live in CSS via `@keyframes`. Every animation SHALL respect `prefers-reduced-motion` through an explicit `@media (prefers-reduced-motion: reduce)` override that suppresses transforms, shakes, and bounces (color flashes and gentle glows MAY remain).

The mobile frontend SHALL maintain a `state.lastSeenActionIndex` (initialized to `-1`) and SHALL evaluate, on every render, whether `(view.last_actions?.length ?? 0) - 1 > state.lastSeenActionIndex`. Only when that condition holds SHALL any animation dispatch run. After dispatch, `state.lastSeenActionIndex` SHALL advance to the newest index. The index SHALL reset to `-1` whenever the phase transitions out of `"playing"`. Re-renders triggered by no-new-action broadcasts (an opponent's pre-lock-in selection toggle, a peer rename, a deck-count change without a play) SHALL NOT replay any animation.

Each animation SHALL add a one-shot class to its target element and SHALL remove that class on the `animationend` event (registered with `{ once: true }`), with a `setTimeout` fallback at `duration + 50ms` for cleanup safety.

The four animations are:

1. **Burn flash** — when `view.last_actions[newest].burned === true`, the frontend SHALL add `.is-burning` to `#m-pile-card`. The keyframe SHALL run ~300 ms and combine a brief warm-accent color flash with a single bounce (`translateY` 0 → ~ -8 px → 0). If no `#m-pile-card` exists at dispatch time, the dispatch SHALL be a silent no-op.

2. **Pickup sweep** — when `view.last_actions[newest].picked_up === true`, the frontend SHALL add `.is-pickup` to the mobile pile container `#m-pile`. The pile keyframe SHALL run ~280 ms with an opacity dip and a small shake (`translateX` ±2 px). Additionally, if the picked-up player is the user (`view.last_actions[newest].player_pid === state.pid`), the frontend SHALL add `.is-pickup` to `#m-hand-row`. The hand-row keyframe SHALL lift the row ~2 px and apply an accent border glow that fades within ~280 ms. The lift SHALL NOT cause any hand card to overlap the sticky action bar.

3. **Illegal-play shake** — when the WebSocket returns an error in response to a mobile `play` message (the existing mobile error toast path), the frontend SHALL add `.is-illegal` to every card element currently carrying `.selected` in `#m-hand-row`. The keyframe SHALL run ~200 ms with a red-tinted shake (`translateX` -3 → +3 → -3 → 0). The existing error toast behavior is unchanged.

4. **Winner celebrate** — when `view.game_over === true` and the mobile end-of-round panel renders, the winner-name `<span>` (`#m-winner-name`) SHALL receive `.is-celebrating`. The keyframe SHALL run ~350 ms with a small grow (`scale` 1.0 → 1.08 → 1.0) plus a soft gold drop-shadow. A `state.celebratedRoundId` (or equivalent gate keyed to the round-ending action index) SHALL ensure the animation fires only once per round.

Animation durations SHALL live in CSS custom properties on `:root` in `static/mobile.css` — `--anim-burn: 300ms`, `--anim-pickup: 280ms`, `--anim-illegal: 200ms`, `--anim-celebrate: 350ms`. WCAG AAA contrast SHALL be preserved at every mid-animation frame; the warm-accent flash color SHALL meet ≥ 7:1 contrast against the mobile pile-card background.

The `@media (prefers-reduced-motion: reduce)` override in `static/mobile.css` SHALL:

- Disable the burn bounce; the color flash MAY remain.
- Disable the pickup shake and hand-row lift; the opacity dip and the static border-glow fade MAY remain.
- Disable the illegal shake; a brief red border on the selected card MAY remain. The toast is unaffected.
- Disable the winner grow; the gold drop-shadow MAY remain as a brief static halo.

Animations SHALL NOT interfere with the mobile sticky action bar's tap targets — at no mid-animation frame SHALL `#m-action-bar` controls become obscured, mis-aligned, or smaller than the existing 44 × 44 px tap floor.

#### Scenario: Burn flash fires on mobile 10-burn

- **WHEN** a state broadcast arrives on the mobile UI where `view.last_actions[-1]` has `burned: true` and the index exceeds `state.lastSeenActionIndex`
- **THEN** `#m-pile-card` receives `.is-burning` for the keyframe duration, then loses it on `animationend`; `state.lastSeenActionIndex` advances

#### Scenario: Mobile burn flash does not fire on no-new-action broadcasts

- **WHEN** a state broadcast arrives where `view.last_actions.length` is unchanged
- **THEN** no class is added to `#m-pile-card`; no animation runs

#### Scenario: Mobile pickup sweep on the user's own pickup

- **WHEN** the user taps Pick up pile and the newest action has `picked_up: true` with `player_pid === state.pid`
- **THEN** both `#m-pile` and `#m-hand-row` receive `.is-pickup`; the hand-row animation does not push any card under the sticky action bar

#### Scenario: Mobile pickup sweep on opponent pickup

- **WHEN** an opponent picks up and the newest action's `player_pid !== state.pid`
- **THEN** `#m-pile` receives `.is-pickup`; `#m-hand-row` does NOT receive the class

#### Scenario: Mobile illegal-play shake on the selected card

- **WHEN** the user taps Play selected with a 6 selected against a pile top of 8 and the server rejects
- **THEN** the selected 6's card button in `#m-hand-row` receives `.is-illegal` for ~200 ms; the mobile error toast appears alongside

#### Scenario: Mobile winner celebrate fires once per round

- **WHEN** the mobile end-of-round panel first renders for a round and `#m-winner-name` receives `.is-celebrating`
- **THEN** the celebration animation runs; subsequent re-renders of the mobile game-over panel within the same round do NOT re-add the class

#### Scenario: Mobile reduced-motion user gets color flash but no bounce

- **WHEN** the user's mobile browser reports `prefers-reduced-motion: reduce` and a burn fires
- **THEN** `#m-pile-card` flashes the warm-accent color but does NOT bounce; no `translateY` is applied

#### Scenario: Mobile action index resets on round end

- **WHEN** a mobile round ends and the host triggers a rematch that transitions back into `"playing"`
- **THEN** `state.lastSeenActionIndex` is `-1` when the first new-round action arrives, so its animation fires correctly

#### Scenario: Mobile reconnect mid-round catches up

- **WHEN** the WebSocket reconnects mid-round and the new state's `last_actions` tail index exceeds the local `state.lastSeenActionIndex`
- **THEN** the renderer dispatches only the newest entry's animation, advances the index, and skips the intermediate entries

#### Scenario: Mobile prefers-reduced-motion overrides exist for all four animations

- **WHEN** `static/mobile.css` is parsed
- **THEN** the `@media (prefers-reduced-motion: reduce)` block contains overrides for each of `.is-burning`, `.is-pickup`, `.is-illegal`, and `.is-celebrating` that disable their transform/shake components

#### Scenario: Action bar tap targets remain accessible during animations

- **WHEN** any of the four animations is running at the moment the user taps `Play selected` or `Pick up pile`
- **THEN** the action-bar buttons remain at ≥ 44 × 44 px and the tap is delivered to the underlying control (animations target the pile, hand row, or winner panel — not the action bar itself)
