## ADDED Requirements

### Requirement: Share room link (desktop)

The desktop lobby SHALL include a **Share link** button positioned next to the room code display. Clicking the button SHALL build a deep-link URL of the form `<location.origin>/room/<state.code>` and attempt the following chain:

1. If `navigator.share` is available, call `navigator.share({ title: "Princess Card Game", text: "Join my Princess room <code>:", url: <link> })`. On success, no further visual confirmation is needed (the OS share sheet *is* the confirmation). On `AbortError` (user dismissal), return silently. On other errors, fall through to step 2.
2. Call `navigator.clipboard.writeText(<link>)`. On success, the button's label SHALL flip to **Copied!** for ~1500 ms then revert to **Share link**.
3. On any failure of both steps, the operation SHALL be a silent no-op (no exception, no toast).

The button SHALL be disabled (or no-op guarded) if `state.code` is unset (e.g., the user is on the landing page before creating/joining a room).

#### Scenario: Button copies URL to clipboard

- **WHEN** the host is in a lobby with `state.code = "AB12"` on a browser without `navigator.share` (or in a secure context where share was declined)
- **THEN** clicking **Share link** copies `<origin>/room/AB12` to the clipboard and the button label briefly reads **Copied!**

#### Scenario: navigator.share opens OS sheet when available

- **WHEN** the host is in a lobby on a browser with `navigator.share`
- **THEN** clicking **Share link** invokes `navigator.share` with the URL `<origin>/room/<code>` and no clipboard write occurs unless the share fails

#### Scenario: User dismisses share sheet silently

- **WHEN** `navigator.share` rejects with `AbortError`
- **THEN** the button's label does not flip to **Copied!** and no clipboard write occurs

#### Scenario: Guard against pre-room click

- **WHEN** the user is on the landing page and (somehow) clicks the Share button before joining/creating a room
- **THEN** no network call is made, no clipboard write occurs, and no exception is thrown
