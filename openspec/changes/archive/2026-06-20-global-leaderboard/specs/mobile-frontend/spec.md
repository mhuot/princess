## ADDED Requirements

### Requirement: Mobile lobby links to Hall of Princesses

The mobile lobby (`/m`) SHALL include a "Hall of Princesses" link in the same switch row that holds the "View desktop site" affordance, pointing to `/leaderboard`. The link SHALL meet the 44 px × 44 px tap-target floor used by the rest of the mobile UI and render at WCAG AAA contrast.

#### Scenario: Link present in mobile lobby

- **WHEN** a user opens `/m` and views the lobby switch row
- **THEN** an anchor labeled "Hall of Princesses" pointing to `/leaderboard` is rendered

#### Scenario: Tap target meets minimum size

- **WHEN** the link is measured
- **THEN** its hit box is at least 44 px × 44 px

#### Scenario: Navigation works

- **WHEN** the user taps the link
- **THEN** the browser navigates to `/leaderboard`
