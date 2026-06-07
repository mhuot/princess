## Context

The working tree is currently a plain directory: 5 capability specs in `openspec/specs/`, 4 archived changes, 105 passing tests, an Apache 2.0 LICENSE, but **no `.git/`** and no GitHub remote. The session's environment header confirms `Is a git repository: false`.

**Decided:** repo will live at `github.com/mhuot/princess`. The active `gh` account has been switched to `mhuot`.

## Goals / Non-Goals

**Goals:**
- A complete, idiomatic open-source project layout that a stranger could clone and play with in under five minutes.
- A CI gate that catches a broken test, an unformatted file, or an invalid OpenSpec change at PR time.
- A vibrant README that sells the project's quirky 7-under variant without burying the quick-start.
- Atomic-commit + docs-sync conventions encoded in `openspec/config.yaml` so future OpenSpec changes inherit them automatically.

**Non-Goals:**
- Containerization (Dockerfile / Compose). The `python -m princess` start is already a one-liner.
- Deployment. Public-facing hosting is a follow-on change.
- Code-coverage gates, security scanning, or dependabot. Add when warranted.
- Multi-Python-version matrix. Pin to 3.14 (the dev version); broaden later if someone files an issue.
- Conventional-commit linting via CI. Keep the commit-format rule as guidance in CONTRIBUTING, enforced by reviewers, not CI.
- A separate docs site (MkDocs, Docusaurus). The README + `openspec/specs/` directory is enough.

## Decisions

### `main` as default, trunk-based with feature branches
**Choice:** Default branch is `main`. Real work happens on short-lived feature branches keyed to an OpenSpec change (e.g. `change/handle-human-exit-mid-game`). Squash-merge into main.
**Why:** Matches the OpenSpec one-change-per-branch flow; lets the CI gate apply to the merged result. Avoids long-running feature branches.

### One commit per OpenSpec task, not one per file
**Choice:** When implementing a change via `/opsx:apply`, each task (`2.1`, `2.2`, …) closes with one commit. Commit message: `<change-name>: <task title>`.
**Why:** Gives a reviewable history where each step matches the spec. Bigger than file-by-file (which produces noise), smaller than one-per-change (which loses traceability).
**Trade-off:** Sometimes one task touches many files; commits will be sometimes large. Acceptable.

### CI runs on push to main + every PR; three workflows, three jobs
**Choice:** Separate `tests.yml`, `lint.yml`, `openspec.yml`. Each runs on `push` to main and `pull_request`. All three must pass for a PR to be mergeable (set as required checks in branch protection — a manual GitHub UI step, not code).
**Why:** Three small workflows make failure attribution obvious in the PR check list. The OpenSpec workflow ensures the spec set stays valid even when changes don't touch source code.
**Alternative considered:** One mega-workflow with three jobs. Equivalent runtime but worse failure UX.

### Python 3.14 only in CI, for now
**Choice:** The dev environment uses Python 3.14.5 (per the venv). CI runs the same.
**Why:** Pre-3.14 wheels for our pinned versions of pydantic and FastAPI worked but required occasional bumps; locking to 3.14 keeps CI deterministic. If a contributor needs 3.12 support, broaden then.

### README structure: tagline → quick start → features → screenshots → docs
**Choice:** Open with a 1-line hook + emoji card art, then *immediately* the 3-line quick start (clone, install, run). Features and the house-rule explanation come AFTER the quick start.
**Why:** Curious visitors want to know "what does it look like running" first. House-rule lore is interesting, but not at the top.

### "Princess only" rule enforced via README + linting (later)
**Choice:** The README, CONTRIBUTING, and `openspec/config.yaml` context all explicitly call out the rename rule ("never use 'shithead' in code, copy, or commits"). A grep-based pre-commit hook is a follow-on; for now it's policy + reviewer.
**Why:** A hard CI check is overkill for a one-developer project, but the rule needs to be discoverable so future agents and contributors don't reintroduce it.

### `.openspec/config.yaml` carries house rules, not the README
**Choice:** OpenSpec project context (`context:` block in `config.yaml`) captures the unique constraints — tech stack, 7-under rule, WCAG AAA, "Princess only" naming — so every future propose/apply session inherits them.
**Why:** README is for humans; config.yaml is for agents. Keeping them in sync is manual; flag drift in CONTRIBUTING's review checklist.

### CHANGELOG starts at `v0.1.0` with retrospective entries
**Choice:** Create CHANGELOG.md with one `[0.1.0]` section listing every capability shipped via the four already-archived changes. Subsequent OpenSpec changes append a `[Unreleased]` bullet that gets cut on tag.
**Why:** A blank changelog looks broken; backfilling captures the project's existing capability surface so newcomers see what's done.

## Risks / Trade-offs

| Risk | Mitigation |
| --- | --- |
| Wrong GitHub owner (`mhuot` vs `michaelhuot_microsoft`) | First task asks the user to confirm/auth before pushing; no code is committed until confirmed. |
| CI burns minutes on every commit | Free tier covers small-project use; if it gets noisy, switch to PR-only triggers later. |
| README screenshot drift as UI changes | CONTRIBUTING includes a "screenshots updated?" checkbox; OpenSpec proposal template adds "docs touched" reminder. |
| Atomic-commit policy slows down active development | Acceptable while the project has one developer; revisit when a third contributor joins. |
| Public repo invites cheating attempts on the multiplayer server | Server is a single-host single-process design; if exploited, host stops it. No persistent state at risk. |
| pylint version drift between local and CI | Pin pylint via `requirements-dev.txt`; CI reuses the same file. |

## Migration Plan

1. Confirm GitHub owner (open question — see below). Do not push code until resolved.
2. `git init` and configure `git config user.name / user.email` from the existing memory (Mike Huot / mhuot@mhuot.net).
3. Write the docs (README, CONTRIBUTING, CHANGELOG, NOTICE, PR/issue templates).
4. Add `.github/workflows/` (tests, lint, openspec).
5. Update `openspec/config.yaml` with project context and atomic-commit / docs-sync rules.
6. `git add -A`; `git commit -m "Initial Princess Card Game release (v0.1.0)"`.
7. `gh repo create <owner>/princess --public --source=. --push` (or, if `mhuot` isn't authed, `gh auth login` first).
8. Watch the first CI run; iterate on any failures (likely lint formatting; the engine is well-tested).
9. Set branch protection rules in the GitHub UI: require the 3 CI checks before merging into `main`.
10. Smoke: clone the repo to a temp dir, run the quick-start from the README, confirm it works.

Rollback: `gh repo delete <owner>/princess --confirm` removes the remote; `rm -rf .git/` would remove local history (not recommended). Far easier: make the repo private.

## Open Questions

- **First tag?** `v0.1.0` matching the CHANGELOG. Defer tagging until after the first CI run is green.

## Resolved Decisions

- **GitHub owner:** `mhuot` — `gh` is authenticated.
- **Repo visibility:** public.
- **Topics:** `card-game`, `climbing-cards`, `fastapi`, `websockets`, `python`, `apache-2`. *No "shithead-variant" topic.*
- **Description:** "A climbing-card game with a 7-under house rule — FastAPI backend, vanilla JS frontend." The "Shithead" descriptor is dropped from anything public-facing per the project's naming rule.
