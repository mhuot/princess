## Why

The Princess Card Game web app has already been built — a multiplayer climbing-card game (Shithead-style) with the house "after a 7, next card under 7" variant. OpenSpec was enabled after the fact, so we need a baseline change that documents the as-built capabilities. Without it, future changes can't reference or amend an existing spec.

This change captures everything currently in the repo as the starting point. No code changes ship with it — it's a documentation-only baseline so subsequent proposals (new rule toggles, persistence, animations, mobile layout, etc.) have a contract to extend.

## What Changes

- Add baseline OpenSpec capability specs that describe the game engine, AI, server, web frontend, and logging subsystems as they exist today.
- Mark implementation tasks complete (already done) so this change can be archived once specs are reviewed.
- No source code is modified by this proposal.

## Capabilities

### New Capabilities

- `game-engine`: Rules, deck, players, hand/face-up/face-down sources, special cards (2 wild reset, 10 burn, 7 reverse-with-optional-7-on-7, four-of-a-kind burn), pre-game swap phase, win/loss detection, and per-room rule configuration.
- `ai-bot`: Heuristic bot player decisions, swap-phase auto-pick, and the bot turn loop with safety bail-outs.
- `room-server`: FastAPI HTTP + WebSocket server, in-memory room registry, room lifecycle (create/join/bot/config/start/rematch/abort/leave), and the play/pickup/set_face_up message protocol.
- `web-frontend`: Browser UI — lobby with rule toggles, setup phase pick-3-of-6, game view with opponents/pile/legend/your-table/hand, end-of-round winner banner with rematch, sort-hand toggle, quit, and accessibility (WCAG AAA contrast, keyboard support, ARIA labels).
- `logging`: In-memory FIFO ring buffer with stdout mirroring, per-room loggers, REST endpoints for paginated read / download / clear, and an in-browser live-tail viewer.

### Modified Capabilities

(none — this is the initial baseline)

## Impact

- **Affected code:** none — this change ships specs only.
- **Affected dependencies:** none.
- **Affected systems:** establishes the OpenSpec spec set at `openspec/specs/`. Future changes will produce deltas against these capabilities.
- **Out of scope:** persistence to disk, multi-process / multi-host scale-out, mobile-specific layout, animation, sound, internationalization. Those would each be follow-on changes that modify or extend these specs.
