## ADDED Requirements

### Requirement: Play & burn animations (desktop)

The desktop frontend SHALL fire subtle CSS-keyframe animations in response to flagged entries appearing in `view.last_actions`. Animations are triggered by JS class-toggling against existing DOM elements; all timing and easing live in CSS via `@keyframes`. Every animation SHALL respect `prefers-reduced-motion` through an explicit `@media (prefers-reduced-motion: reduce)` override that suppresses transforms, shakes, and bounces (color flashes and gentle glows MAY remain).

The frontend SHALL maintain a `state.lastSeenActionIndex` (initialized to `-1`) and SHALL evaluate, on every render, whether `(view.last_actions?.length ?? 0) - 1 > state.lastSeenActionIndex`. Only when that condition holds — i.e., a NEW action entry has appeared — SHALL any animation dispatch run. After dispatch, `state.lastSeenActionIndex` SHALL advance to the newest index. The index SHALL reset to `-1` whenever the phase transitions out of `"playing"` (game-over → rematch → setup → playing). Re-renders triggered by an opponent's pre-lock-in selection toggle, a peer rename, or any other no-new-action broadcast SHALL NOT replay any animation.

Each animation SHALL add a one-shot class to its target element and SHALL remove that class on the `animationend` event (registered with `{ once: true }`), with a `setTimeout` fallback at `duration + 50ms` to guarantee cleanup if `animationend` does not fire (e.g., under a reduced-motion override that disables the animation entirely).

The four animations are:

1. **Burn flash** — when `view.last_actions[newest].burned === true`, the frontend SHALL add `.is-burning` to `#pile-card` (the discard's top card). The keyframe SHALL run ~300 ms and combine a brief warm-accent color flash with a single bounce (`translateY` 0 → ~ -8 px → 0). If no `#pile-card` element exists at the moment of dispatch (e.g., a chain-burn cleared the pile and the next state has not yet placed a new card), the dispatch SHALL be a silent no-op for that entry.

2. **Pickup sweep** — when `view.last_actions[newest].picked_up === true`, the frontend SHALL add `.is-pickup` to `.pile-area`. The pile-area keyframe SHALL run ~280 ms and dip opacity briefly while applying a small shake (`translateX` ±2 px). Additionally, if the picked-up player is the user (`view.last_actions[newest].player_pid === state.pid`), the frontend SHALL add `.is-pickup` to `#hand-row` (the user's hand container). The hand-row keyframe SHALL lift the row ~2 px and apply an accent border glow that fades within ~280 ms. If the picker is an opponent, the hand-row animation SHALL NOT run.

3. **Illegal-play shake** — when the WebSocket returns an error in response to a `play` message (the existing `showError(msg)` path), the frontend SHALL add `.is-illegal` to every card element currently carrying `.selected`. The keyframe SHALL run ~200 ms with a red-tinted shake (`translateX` -3 → +3 → -3 → 0). The existing error toast behavior is unchanged.

4. **Winner celebrate** — when `view.game_over === true` and the game-over panel renders, the winner-name `<span>` (`#winner-name`) SHALL receive the class `.is-celebrating`. The keyframe SHALL run ~350 ms with a small grow (`scale` 1.0 → 1.08 → 1.0) plus a soft gold drop-shadow. A `state.celebratedRoundId` (or equivalent gate keyed to the round-ending action index) SHALL ensure the animation fires only once per round; subsequent game-over re-renders within the same round SHALL NOT replay the animation.

Animation durations SHALL live in CSS custom properties on `:root` — `--anim-burn: 300ms`, `--anim-pickup: 280ms`, `--anim-illegal: 200ms`, `--anim-celebrate: 350ms` — and keyframes SHALL reference them via `animation-duration`. WCAG AAA contrast SHALL be preserved at every mid-animation frame; the warm-accent flash color SHALL meet ≥ 7:1 contrast against the pile-card background.

The `@media (prefers-reduced-motion: reduce)` override SHALL:

- Disable the burn bounce; the color flash MAY remain.
- Disable the pickup shake and hand-row lift; the opacity dip and the static border-glow fade MAY remain.
- Disable the illegal shake; a brief red border on the selected card MAY remain. The toast is unaffected.
- Disable the winner grow; the gold drop-shadow MAY remain as a brief static halo.

#### Scenario: Burn flash fires on a 10-burn

- **WHEN** a state broadcast arrives where `view.last_actions[-1]` has `burned: true` and that index exceeds `state.lastSeenActionIndex`
- **THEN** the `#pile-card` element receives the `.is-burning` class for the duration of the keyframe, then loses it on `animationend`; `state.lastSeenActionIndex` advances to the new index

#### Scenario: Burn flash does not fire on a peer's selection toggle

- **WHEN** a state broadcast arrives where `view.last_actions.length` is unchanged from the previous render (an opponent toggled a setup selection)
- **THEN** no class is added to `#pile-card`; no animation runs

#### Scenario: Pickup sweep on the user's own pickup animates both pile and hand

- **WHEN** the user picks up the pile and the newest action has `picked_up: true` with `player_pid === state.pid`
- **THEN** both `.pile-area` and `#hand-row` receive `.is-pickup`; the hand-row animation lifts and glows briefly

#### Scenario: Pickup sweep on an opponent's pickup animates only the pile

- **WHEN** an opponent picks up the pile (`picked_up: true`, `player_pid !== state.pid`)
- **THEN** `.pile-area` receives `.is-pickup`; `#hand-row` does NOT receive the class

#### Scenario: Illegal-play shake on the selected card

- **WHEN** the user clicks Play with a 6 selected against a pile top of 8 and the server rejects the play
- **THEN** the selected 6's card button receives `.is-illegal` for ~200 ms; the existing error toast appears alongside

#### Scenario: Winner celebrate fires once per round

- **WHEN** the game-over panel first renders for a round and the winner-name span is mounted with `.is-celebrating`
- **THEN** the celebration animation runs; subsequent re-renders of `#game-over` within the same round (e.g., on a state broadcast prior to rematch) do NOT re-add the class

#### Scenario: Reduced-motion user gets the color flash but no bounce

- **WHEN** the user's browser reports `prefers-reduced-motion: reduce` and a burn fires
- **THEN** `#pile-card` flashes the warm-accent color but does NOT bounce; no `translateY` is applied

#### Scenario: Action index resets on round end

- **WHEN** a round ends (`view.game_over` becomes true) and the host triggers a rematch that transitions the phase back into `"setup"` then `"playing"`
- **THEN** `state.lastSeenActionIndex` is `-1` at the moment the first `last_actions` entry of the new round arrives, so the first action's animation fires correctly

#### Scenario: Reconnect mid-round catches up

- **WHEN** the WebSocket reconnects mid-round and the new state broadcast contains a `last_actions` list whose tail index exceeds the local `state.lastSeenActionIndex`
- **THEN** the renderer dispatches the animation for the newest entry (not for every missed entry in between); the index advances to the latest

#### Scenario: prefers-reduced-motion overrides exist for all four animations

- **WHEN** `static/styles.css` is parsed
- **THEN** the `@media (prefers-reduced-motion: reduce)` block contains overrides for each of `.is-burning`, `.is-pickup`, `.is-illegal`, and `.is-celebrating` that disable their transform/shake components
