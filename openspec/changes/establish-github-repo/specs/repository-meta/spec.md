## ADDED Requirements

### Requirement: README is the front door

The repository SHALL include a top-level `README.md` that opens with a one-line tagline + visual element (emoji card art is sufficient), followed by a 3-step quick-start (clone, install, run) **before** any feature list or lore. The README SHALL link to `CONTRIBUTING.md`, `CHANGELOG.md`, the `LICENSE`, and the OpenSpec workflow. The 7-under house rule SHALL be called out prominently as the project's defining variant.

#### Scenario: Quick start visible without scrolling

- **WHEN** a visitor opens `README.md` on GitHub at default viewport
- **THEN** the tagline, an emoji-card visual, and the three setup commands are visible within the first screenful (above the features list)

#### Scenario: Links to supporting docs

- **WHEN** the README is rendered
- **THEN** it contains active links to `CONTRIBUTING.md`, `CHANGELOG.md`, `LICENSE`, and the `openspec/` directory

#### Scenario: House rule prominent

- **WHEN** the README is rendered
- **THEN** a dedicated section describes the 7-under house rule (and that another 7 is also legal by default) before any general "rules" overview

### Requirement: License + attribution files

The repository SHALL include `LICENSE` (Apache 2.0 full text) and `NOTICE` (boilerplate identifying the Work, Licensor, year, and any third-party attributions). Every source file under `princess/` and `tests/` SHALL carry the Apache 2.0 header comment block with the current year and "Mike Huot" as the copyright holder.

#### Scenario: LICENSE present

- **WHEN** the repository root is listed
- **THEN** a file named `LICENSE` exists containing the unmodified Apache License 2.0 text

#### Scenario: Every Python source file has a header

- **WHEN** any file under `princess/` or `tests/` is opened
- **THEN** its first ~12 lines include `Copyright <year> Mike Huot` and `Licensed under the Apache License, Version 2.0`

### Requirement: CHANGELOG follows Keep a Changelog

The repository SHALL include `CHANGELOG.md` following the "Keep a Changelog" format (https://keepachangelog.com). The file SHALL begin with an `## [Unreleased]` section for in-flight changes, followed by released versions in reverse chronological order. The initial release SHALL be tagged `0.1.0` and SHALL summarize the capabilities shipped via the four already-archived OpenSpec changes (`baseline`, `pickup-passes-turn`, `show-last-three-moves` [if applied by tag time], `handle-human-exit-mid-game`).

#### Scenario: Unreleased section present

- **WHEN** `CHANGELOG.md` is opened
- **THEN** an `## [Unreleased]` heading appears before any version-tagged section

#### Scenario: Initial release lists shipped capabilities

- **WHEN** the `## [0.1.0]` section is rendered
- **THEN** it includes bullets covering the game engine, AI bot, server, frontend, logging, swap phase, 7-on-7 toggle, bot-name roster, structured logging, log viewer, quit modal, bot takeover, and orphan room cleanup

### Requirement: CONTRIBUTING.md documents dev workflow

The repository SHALL include `CONTRIBUTING.md` describing: local setup (venv + `requirements-dev.txt`), format command (`black princess tests`), lint command (`pylint princess tests`), test command (`pytest`), the OpenSpec change workflow with `/opsx:propose` → `/opsx:apply` → `/opsx:archive`, the commit message format (`<change-name>: <task title>` for OpenSpec-driven work), and a PR checklist that includes "docs (README/CHANGELOG) updated if surfaces changed."

#### Scenario: All four dev commands present

- **WHEN** `CONTRIBUTING.md` is rendered
- **THEN** it contains the four exact commands above in a "Quickstart" or "Dev setup" section

#### Scenario: PR checklist includes docs reminder

- **WHEN** the "PR checklist" section is rendered
- **THEN** one item explicitly reminds the contributor to update README/CHANGELOG when user-visible surfaces change

### Requirement: GitHub PR + issue templates

The repository SHALL include `.github/PULL_REQUEST_TEMPLATE.md` (with sections: Summary, Related OpenSpec change, Docs touched, Test plan) and at least two issue templates under `.github/ISSUE_TEMPLATE/` named `bug_report.md` and `feature_request.md`.

#### Scenario: PR template prompts for the OpenSpec link

- **WHEN** a new PR is opened
- **THEN** the body pre-populates with a field named "Related OpenSpec change" (or equivalent) prompting the author to link the originating change

### Requirement: CI runs tests, lint, and OpenSpec validation

The repository SHALL define three GitHub Actions workflows under `.github/workflows/`:

- `tests.yml` — runs `pytest -q` on Python 3.14, `ubuntu-latest`, on `push` to `main` and on `pull_request`.
- `lint.yml` — runs `black --check princess tests` and `pylint princess tests`.
- `openspec.yml` — runs `openspec validate --specs --strict` and `openspec validate <all active changes> --strict`.

All three workflows SHALL be required for a PR to be marked mergeable (configured via GitHub branch-protection rules, which are stored outside the repo). A failing workflow SHALL block merge.

#### Scenario: tests.yml runs on PR

- **WHEN** a PR is opened or updated against `main`
- **THEN** the `tests` workflow runs and reports pass/fail on the PR's "Checks" tab

#### Scenario: openspec validate covers active changes

- **WHEN** the `openspec` workflow runs
- **THEN** it executes both `openspec validate --specs --strict` and, for each directory under `openspec/changes/<name>/` (excluding `archive/`), `openspec validate <name> --strict`

### Requirement: OpenSpec config carries project context + workflow rules

`openspec/config.yaml` SHALL be populated with:

- A `context:` block describing the tech stack, the project's house rules (7-under, 2 wild, 10 burn, four-of-a-kind burn), the WCAG AAA contrast target, the "Princess only" naming rule, the Apache 2.0 license + Mike Huot copyright, and the Python 3.14 dev target.
- A `rules.tasks:` entry stating "One commit per task, message `<change-name>: <task title>`."
- A `rules.proposal:` entry stating "Include a 'Docs touched' line in the Impact section when user-visible surfaces change."

#### Scenario: Future propose inherits the context

- **WHEN** a new propose call retrieves `openspec instructions`
- **THEN** the `context` field of the returned JSON includes the house rules and naming policy text

#### Scenario: Atomic commit rule visible to apply

- **WHEN** an apply session calls `openspec instructions apply`
- **THEN** the tasks artifact's rules include the one-commit-per-task guidance

### Requirement: Atomic commits and docs-in-sync policy

OpenSpec-driven changes SHALL produce one git commit per task in `tasks.md`. Each commit's message SHALL begin with the change name, followed by a colon and the task's title (e.g. `establish-github-repo: Write CONTRIBUTING.md`). User-visible behavior changes SHALL be accompanied by README and/or CHANGELOG updates within the same change (and the same set of commits) — they MUST NOT lag behind code.

#### Scenario: A change that touches a UI requirement updates README

- **WHEN** an apply session modifies any frontend file under `static/` for a user-visible behavior
- **THEN** the same change's commit set also touches `README.md` (and `CHANGELOG.md` for non-trivial changes)

#### Scenario: One commit per task

- **WHEN** an apply session completes tasks 2.1 through 2.4
- **THEN** the git log shows four commits, each named `<change>: <task title>`
