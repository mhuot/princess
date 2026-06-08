## ADDED Requirements

### Requirement: "Mobile site" footer link

The desktop UI footer SHALL include a "Mobile site" link in the same area as the existing "View logs" link. Clicking it SHALL:

1. Clear the `princess_prefer_desktop` cookie (so the server is free to redirect future requests to `/m` based on UA).
2. Navigate to `/m`.

#### Scenario: Mobile site link present

- **WHEN** the desktop footer is rendered
- **THEN** an element with `id="switch-to-mobile"` is visible and links to `/m`

#### Scenario: Click clears the desktop-preference cookie

- **WHEN** the user clicks `#switch-to-mobile` on a page where the `princess_prefer_desktop` cookie was set
- **THEN** the cookie is cleared (set to expire in the past) before navigation completes
