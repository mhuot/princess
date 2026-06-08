## MODIFIED Requirements

### Requirement: Share room link (mobile)

The mobile UI SHALL include a **Share** affordance — typically a small icon button labelled `↗` with `aria-label="Share room link"` — in two places:

1. In the **mobile lobby**, positioned next to the room-code line.
2. In the **game-view top bar**, positioned alongside the existing room-code chip / Rename / Quit buttons.

Tapping either Share affordance SHALL build a deep-link URL of the form `<location.origin>/m/<state.code>` and attempt the following chain:

1. If `navigator.share` is available, call `navigator.share({ title: "Princess Card Game", text: "Join my Princess room <code>:", url: <link> })`. On success, no further confirmation is needed. On `AbortError` (user dismissal), return silently. On other errors, fall through to step 2.
2. Call `navigator.clipboard.writeText(<link>)`. On success, the **clicked button's own text glyph** SHALL temporarily change from `↗` to `✓` for approximately 1500 ms then revert. (No separate toast element is used; the previous attempt to flash a message inside `#m-lobby-error` was unreachable because `#m-lobby-error` lives inside `#m-landing` which is hidden once a room is created.)
3. On any failure of both steps, the operation SHALL be a silent no-op.

The existing tap-to-copy on the game-view room-code chip — which copies *just the code* (`state.code`) — remains in place for voice-dictation flows. The new Share button is additive.

#### Scenario: Mobile share invokes navigator.share

- **WHEN** the user taps the lobby Share button on a mobile browser with `navigator.share`
- **THEN** `navigator.share` is invoked with URL `<origin>/m/<state.code>` and no clipboard write occurs unless the share fails

#### Scenario: Mobile share falls back to clipboard with button-glyph flash

- **WHEN** the user taps a Share button on a browser without `navigator.share`
- **THEN** the URL `<origin>/m/<state.code>` is written to the clipboard, and the clicked button's text content changes from `↗` to `✓` for about 1500 ms before reverting

#### Scenario: Mobile share in game view top bar works

- **WHEN** the user taps the game-view top bar Share button while in a live round
- **THEN** the same share/clipboard chain runs against the URL `<origin>/m/<state.code>`; on the clipboard-fallback path, the game-view Share button (not the lobby one) flashes the `✓` glyph

#### Scenario: Code-only tap-to-copy still works

- **WHEN** the user taps the room-code *chip* (not the Share button) in the game-view top bar
- **THEN** only the bare code (e.g., `"AB12"`) is copied to the clipboard, not a URL

#### Scenario: Share button respects accessibility size

- **WHEN** the lobby or game-view Share button is rendered
- **THEN** its bounding box is at least 44 × 44 logical pixels
