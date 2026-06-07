## Context

Princess Card Game is a single-deck climbing-card game (a Shithead/Karma variant) implemented as a web app for casual local + internet multiplayer. The house variant is "after a 7, the next card must be UNDER 7," with an optional 7-on-7 allowance enabled by default. The codebase already runs end-to-end: a Python backend serves both the API/WebSocket and the static frontend; a vanilla-JS browser app handles the UI.

Stakeholders: a single user (Mike Huot) playing casually, sometimes alone against AI, sometimes with friends over the internet who join via short room code.

Hard constraints (per the project's global instructions):
- Apache 2.0 license, Apache 2.0 headers on source files.
- Python 3.x with `venv`, pylint, black, PEP 8.
- WCAG AAA color contrast in the UI.
- Use "Princess" in user-facing copy — never the inspiring game's vulgar name.

## Goals / Non-Goals

**Goals:**
- Provide an authoritative server-side rules engine so cheating is impossible from the browser.
- Run on one process with no external services (no database, no Redis, no separate worker) so the user can start it with one command (`python -m princess`).
- Be playable solo (with bots filling seats) and with friends over the internet (single room code).
- Make the unusual house rule (7 reverse, 7-on-7 optional) obvious in the UI and easy to toggle per room.
- Provide enough server-side observability that any future freeze can be diagnosed by reading the in-browser log viewer.

**Non-Goals:**
- Persistence. Rooms and games are lost on restart. No accounts, no history.
- Horizontal scale. The in-memory registry assumes a single process. Multi-host would need a shared store and would be a follow-on change.
- Reconnection. If a player's WebSocket drops, they can refresh the same `/room/<code>` URL and re-attach by `pid` — but only as long as the same browser tab still has the pid in memory.
- Mobile-optimized layout. The layout is responsive in a basic way (smaller cards under 600px) but not designed for thumbs.
- Animations or sound.

## Decisions

### Authoritative server, thin client
**Choice:** All game logic lives in `princess.game.Game`. The frontend only sends user intent (`play` / `pickup` / `set_face_up`) and renders the broadcast state. It does perform a *display-only* legality check (green outline on legal cards) but the server ignores the client's verdict.
**Why:** Prevents cheating, keeps a single source of truth, makes the rules unit-testable without a browser. Trade-off: every action round-trips through WebSocket — fine on LAN/internet, would be sluggish only with hundreds of plays per second.
**Alternatives:** A client-side engine syncing via CRDTs (over-engineered for ≤4 players in one room) or a stateless server that re-derives state from a log (more failure modes, no real benefit at this scale).

### In-memory rooms, no database
**Choice:** `RoomRegistry` is a dict in process memory. Rooms vanish on restart.
**Why:** Matches the casual single-user use case. Adding Postgres or even SQLite would dwarf the rest of the codebase.
**Trade-off:** Server restart loses all in-flight rooms. Acceptable — players just refresh and start again.
**Future:** A persistence capability could be added later as a new change that introduces a `Store` interface with a default in-memory impl.

### Per-room rule config via a small dataclass
**Choice:** `GameConfig` is a frozen-ish dataclass with one toggle so far (`seven_on_seven`). New rules are added by adding fields with sensible defaults.
**Why:** A dict would be flexible but un-typed and easy to typo. The dataclass gives autocomplete and a deserialization shim (`from_dict`) that ignores unknown keys, so old clients don't break new servers.

### FastAPI + WebSockets, vanilla JS frontend
**Choice:** FastAPI for HTTP and the WebSocket abstraction; plain ES2020 JavaScript on the client (no bundler, no framework).
**Why:** Single-binary deploy, no build step for the client, no JS dependency lock-in. The UI is small enough that a framework's structure isn't worth its weight.
**Trade-off:** The `app.js` file is long and procedural. Refactoring into modules is a future concern.

### Synchronous bot turns under the WebSocket lock
**Choice:** After every human action, the WS message handler awaits `run_bots()`, which advances the game until a human is current again, broadcasting state after each bot action with a 0.6s "think" delay.
**Why:** Deterministic ordering; no separate scheduler. The 0.6s delay makes the bots feel paced rather than instant.
**Risk:** A buggy AI decision could loop forever, freezing the room. Mitigation: hard cap of 30 actions per turn + force-pickup fallback when `decide()` produces an action the engine rejects (the bug that already caused one freeze, now fixed).

### Pre-game swap as a Game-level phase
**Choice:** Setup is modeled inside `Game` as `phase == "setup"`. `set_face_up()` is just another action; bots auto-pick at room start.
**Why:** Keeps the state machine cohesive — `view_for()` already returns everything the UI needs, so setup is just another render path. Alternative would be a separate "pre-game" object and a phase transition handled in `Room`, which fragments state.

### In-memory FIFO log buffer + browser viewer
**Choice:** Logs go to stdout *and* to a 2000-entry `collections.deque`. The browser polls `/api/logs?since=<id>` and renders new lines; `/api/logs/download` returns the whole buffer as a text attachment.
**Why:** User explicitly didn't want a filesystem footprint. The ring keeps memory bounded (~250KB at typical line length). Polling is fine at 2-second cadence; switching to Server-Sent Events would be a tiny win for a lot more code.
**Risk:** Restarting the server loses the buffer. Acceptable for an MVP — the download button covers "save this game's logs before stopping the server."

### Vanilla CSS with WCAG AAA palette
**Choice:** Hand-rolled CSS with explicit color tokens (`--bg`, `--ink`, `--accent`) targeting ≥7:1 contrast for normal text.
**Why:** Required by the project's global instructions. Easy to verify, no framework lock-in.

## Risks / Trade-offs

| Risk | Mitigation |
| --- | --- |
| Single-process state loss on crash/restart | Acceptable for solo + small-group casual use; the rematch flow makes "start fresh" cheap. |
| Bot infinite loop freezing a room | 30-action safety cap, force-pickup on rejection, exception fallback, all instrumented in the log buffer. |
| Frontend's display-only legality check drifts from the engine | Both consult `view.config` from the same broadcast; if they disagree, the engine's rejection bubbles back as an error toast and a `WARN` log line. |
| WebSocket lost mid-game | Browser refresh on `/room/<code>` re-attaches the same `pid` if still in tab memory; otherwise the seat is effectively orphaned until the host kicks (no kick UI yet — manual abort works). |
| 100-bot-name pool exhausted in a single tiny room | Fallback to `Bot <4-digit>` after the pool is drained — bounded code in `pick_bot_name`. |
| Future rule toggles balloon `GameConfig` | The dataclass is unbounded; revisit if it gets past ~8 fields and consider grouping. |

## Migration Plan

This change is documentation-only — no code ships with it.

- Land the baseline specs at `openspec/specs/<capability>/spec.md`.
- Archive the change.
- Future changes (e.g., "Add more rule toggles") will produce delta specs under `openspec/changes/<change>/specs/<capability>/spec.md`.

No rollback needed; reverting the proposal means deleting the spec files.

## Open Questions

- Should reconnection-by-pid (persistent across browser refresh, not just same tab) be its own near-term change? Likely yes — a tiny localStorage stash of `pid` per `code` would suffice.
- Do we want a "spectator" capability for non-playing observers? Out of scope for the baseline.
- How should disconnected human players be handled mid-game — auto-converted to a bot, skip-them-on-turn, or freeze the round? Currently the room just waits; an idle timeout would be a follow-on change.
