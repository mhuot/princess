## ADDED Requirements

### Requirement: Desktop footer links to Hall of Princesses

The desktop page (`/`) SHALL include a "Hall of Princesses" link in its footer that navigates to `/leaderboard`. The link SHALL be a regular `<a>` with the same focus-ring treatment as the existing footer links, accessible via Tab order, and visible at WCAG AAA contrast against the footer background.

#### Scenario: Link present in desktop footer

- **WHEN** a user loads `/`
- **THEN** an anchor with accessible name "Hall of Princesses" pointing to `/leaderboard` is present in the footer

#### Scenario: Keyboard reachable

- **WHEN** a keyboard user tabs through the footer
- **THEN** the link receives a visible focus ring before being activated
