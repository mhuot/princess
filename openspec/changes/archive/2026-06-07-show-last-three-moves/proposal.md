## Why

Right now the game UI surfaces a single `last_action` string ("Lady L33t played 6S — your turn"). When the bot loop fires off two or three moves in a row (a burn + replay, a 4-of-a-kind chain, or two consecutive bot turns), the player only sees the **most recent** message — the earlier moves vanish before they can be read. The pile area shows the top card but not how it got there.

Showing the last three moves gives the player enough scrollback to follow what just happened, especially during a multi-step bot turn.

## What Changes

- Replace the engine's `last_action: str` with a bounded history of the last 3 actions (newest first or last — see Design). The current "single string" is becoming a list.
- Each entry includes: the actor's name, a short verb phrase ("played 8H, 8D", "picked up the pile", "burned!"), and a flag for special events (burn, finish, pickup).
- Broadcast state includes the history list under `public_state.last_actions` (renamed from `last_action`). Old key remains available for one release as a fallback so existing test clients don't snap.
- Frontend status line becomes a small stack of up to three lines, newest highlighted, older lines dimmed.
- `aria-live="polite"` region still announces only the newest line so a screen reader isn't re-read everything on each update.
- Setup-phase "deal complete — game on!" message also goes through the same history (so the player can see the deal happen before the first move).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `game-engine`: replace the single `last_action` field with a bounded `last_actions` list (max 3 entries, newest at the end).
- `web-frontend`: status line renders up to three past actions stacked, with the most recent emphasized.

## Impact

- **Affected code:**
  - `princess/game.py` — `Game.last_action` → `Game.last_actions: list[dict]`; every assignment site (six or so) now appends to the bounded list.
  - `princess/server.py` and `princess/rooms.py` — no logic change; broadcasts the new field.
  - `static/app.js` — `renderStatus()` walks the list; `renderLegend()` and other render paths read `view.last_actions`.
  - `static/styles.css` — new `.status-stack` styling.
  - `static/index.html` — `#status-line` becomes `#status-stack` (or a wrapper around multiple lines).
- **Affected APIs:** the serialized state dict adds `last_actions`. The legacy `last_action` key may be removed in a follow-on change once any external consumer (none today) has adopted the new field.
- **Affected dependencies:** none.
- **Depends on:** `baseline-princess-card-game` archived (modifies `game-engine` and `web-frontend` baselines).
