## MODIFIED Requirements

### Requirement: README is the front door

The repository SHALL include a top-level `README.md` that opens with a one-line tagline + visual element (emoji card art is sufficient), followed by a 3-step quick-start (clone, install, run) **before** any feature list or lore. The README SHALL link to `CONTRIBUTING.md`, `CHANGELOG.md`, the `LICENSE`, and the OpenSpec workflow.

The README SHALL describe the project's signature **reverse-rank house rule** in a dedicated section, naming the default reverse rank as **5** and explaining that the rank is configurable per room via the lobby's House rules panel. The section SHALL clarify that **2** (wild reset) and **10** (burn) remain unconditionally legal regardless of the reverse rank.

#### Scenario: Quick start visible without scrolling

- **WHEN** a visitor opens `README.md` on GitHub at default viewport
- **THEN** the tagline, an emoji-card visual, and the three setup commands are visible within the first screenful (above the features list)

#### Scenario: Links to supporting docs

- **WHEN** the README is rendered
- **THEN** it contains active links to `CONTRIBUTING.md`, `CHANGELOG.md`, `LICENSE`, and the `openspec/` directory

#### Scenario: Reverse-rank section mentions default and configurability

- **WHEN** the README is rendered
- **THEN** a dedicated section names **5** as the default reverse rank, explains the under-the-rank rule, and notes that the rank is tunable per room (with a pointer to the lobby's "House rules" panel)

#### Scenario: Special cards (2 and 10) called out

- **WHEN** the reverse-rank section is rendered
- **THEN** it explicitly states that 2 (wild reset) and 10 (burn) remain unconditionally legal regardless of the configured reverse rank
