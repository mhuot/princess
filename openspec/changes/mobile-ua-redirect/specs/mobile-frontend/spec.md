## ADDED Requirements

### Requirement: "View desktop site" link

The mobile UI lobby footer area SHALL include a "View desktop site" link/button (`id="m-switch-to-desktop"`). Tapping it SHALL:

1. Set the cookie `princess_prefer_desktop=1; Path=/` so future requests to `/` are not redirected back to `/m`.
2. Navigate to `/`.

The link SHALL be styled as a small, low-emphasis text link (not a primary action) to avoid competing with the create/join controls.

#### Scenario: Desktop-switch link present

- **WHEN** the mobile lobby is rendered
- **THEN** an element with `id="m-switch-to-desktop"` is visible

#### Scenario: Tap sets the cookie and navigates

- **WHEN** the user taps `#m-switch-to-desktop`
- **THEN** the cookie `princess_prefer_desktop=1` is set on the document and the browser navigates to `/`

#### Scenario: Round trip stays consistent

- **WHEN** the user tapped "View desktop site" on `/m` and then taps "Mobile site" on `/`
- **THEN** the cookie is cleared, the browser navigates to `/m`, and refreshing `/` will redirect to `/m` based on UA
