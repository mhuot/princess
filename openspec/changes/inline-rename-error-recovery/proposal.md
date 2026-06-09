## Why

The `unique-room-names` change added server-side dedupe — rename now returns **409** when the requested name collides with another seat. But the desktop inline-rename UX trades the input for a static name span the moment the user hits Enter or blurs, *before* the POST resolves. When the 409 comes back, the user sees a red error in `#lobby-error` and has to start over: click **Rename** again, retype, resubmit. Two extra clicks and a fresh type for a one-character fix.

The mobile rename sheet already handles this correctly — the sheet only `.close()`s inside the try-block of `submitRename`, so on error the sheet stays open with the offending name still in the input. But mobile does not visually surface the error inside the sheet (it goes to the generic mobile error helper), and there's no scenario locking the behavior in. Close both gaps.

The 422 (overlength) path has the same friction shape and should be handled identically — any 4xx response should keep the input open so the user can correct without re-opening the rename UI.

## What Changes

- **Desktop inline rename (`static/app.js`, `beginRenameInline` + `renameSelf`):**
  - The input SHALL NOT be replaced with the name span until the rename POST resolves successfully.
  - On any 4xx response (409 collision, 422 overlength, etc.), the input SHALL remain in place, the error SHALL surface in `#lobby-error` (existing slot — no new DOM element), the input SHALL be re-focused, and its current contents SHALL be programmatically selected so the user can type over them immediately.
  - On success, the input SHALL collapse back to the new name (the lobby re-render triggered by the broadcast already replaces it, but the local handler SHALL also tear down the input as a fallback in case the broadcast lags).
  - Escape SHALL still cancel without a POST and restore the original name span.
  - Blur with an unchanged value SHALL collapse without a POST (no-op, same as today).
  - While the POST is in flight the input SHALL be `disabled` to prevent double-submit (a sibling spinner is out of scope; latency is sub-50ms typical).
- **Mobile rename sheet (`static/mobile.js`, `submitRename` + `#m-rename-sheet`):**
  - Verify the existing behavior: sheet remains open on POST failure because `close()` is only called in the `try` branch. (Confirmed during proposal write.)
  - Add: on 4xx the input SHALL be re-focused and its contents selected so the user can immediately edit. The error already shows via the global mobile error helper; no new toast is required.
- **Game-view rename (desktop and mobile Rename buttons in the game header):**
  - Desktop `promptRenameForGame` uses a native `window.prompt`; on 4xx the user can re-trigger Rename. No behavior change beyond what the underlying `renameSelf` already does (its catch surfaces the error). Documented for completeness; no spec scenario added.

## Capabilities

### Modified Capabilities

- `web-frontend`: the lobby Rename requirement gains "keep input open on error + focus + select" behavior with new scenarios.
- `mobile-frontend`: the mobile lobby Rename requirement gains an "error keeps the sheet open + refocus input" scenario.

### New Capabilities

(none)

## Impact

- **Affected code:**
  - `static/app.js` — refactor `beginRenameInline` so `submit()` awaits the POST before tearing down the input; on rejection re-focus + select; expose a small helper so `renameSelf` can signal success/failure back to the caller (or inline the POST inside `beginRenameInline` and drop the intermediate function — implementation detail decided in `design.md`).
  - `static/mobile.js` — minor: after `showError(...)` in the `catch` of `submitRename`, also call `$("m-rename-input").focus(); $("m-rename-input").select()`.
  - `static/styles.css` — possibly a `.rename-input.is-busy` (disabled-state) style; minor.
- **Affected APIs:** none. Server stays unchanged — the 409 / 422 contract from `unique-room-names` and the existing Pydantic length validator already do the right thing.
- **Affected dependencies:** none.
- **Docs touched:** `CHANGELOG.md` `[Unreleased]` `### Changed` — one line.
- **Out of scope:**
  - Pre-validating the name client-side before submit. The server's dedupe is the source of truth; the round-trip is cheap.
  - Showing the error *inside* the lobby Rename row (a new inline `.rename-error` element). The existing `#lobby-error` slot is right above the seat list and is the established error surface. Adding a per-row error sticker is more DOM for marginal gain.
  - Suggesting alternative names ("Mike 2") on collision. Same reasoning as `unique-room-names` proposal.
  - Auto-retry. The user has to pick a different name; there's nothing to retry without input.
  - Mid-round (`promptRenameForGame`) UX upgrade. The native `prompt()` re-opens on failure if the user clicks Rename again; a polished inline replacement is a separate change.
