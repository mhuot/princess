## Why

Princess Card Game has reached a polished local state: 105 tests pass, 5 OpenSpec capabilities are documented, the rules engine + bot + multiplayer server + frontend + logs viewer all work end-to-end. The project is one user (Mike) locally, with no version control, no public face, and no automated quality gate.

Time to make it shareable. Friends should be able to clone, run a single command, and play. New contributions — whether spec changes via OpenSpec or direct PRs — need a CI gate so the test suite and spec validation stay green. The README should be a vibrant front door that makes the project look as fun as it is, with the 7-under house rule highlighted up front.

The OpenSpec workflow needs a small upgrade too: codify the conventions we've been informally following so future agents and humans get them automatically — atomic commits per task, docs updated alongside code, CI green before archive.

## What Changes

- **Initialize git** in `/Users/mhuot/princess` (currently not a repo per the session's environment header), commit the existing code as an initial Apache 2.0 release.
- **Create a public GitHub repository** at `github.com/mhuot/princess` (or `github.com/MikeHuot/princess` — see "Open questions" in design), push the initial commit, and set `main` as the default branch.
- **Vibrant `README.md`** as the project's front door:
  - Hero tagline + emoji card art.
  - Status badges (CI, license, Python version).
  - One-liner setup + run instructions.
  - Feature list including the 7-under house rule, 100-name bot roster, in-browser log viewer.
  - Screenshot placeholder block (real screenshot added after initial smoke).
  - Pointers to CONTRIBUTING, CHANGELOG, OpenSpec workflow.
- **Supporting docs:**
  - `CONTRIBUTING.md` — dev setup, format/lint/test commands, OpenSpec change workflow, commit message format, PR checklist.
  - `CHANGELOG.md` — "Keep a Changelog" format; initial v0.1.0 entry summarizing every capability shipped via the archived changes.
  - `NOTICE` — Apache 2.0 attribution boilerplate.
  - `.github/PULL_REQUEST_TEMPLATE.md` — short template that references the OpenSpec workflow.
  - `.github/ISSUE_TEMPLATE/bug_report.md` + `feature_request.md`.
- **GitHub Actions workflows (`.github/workflows/`):**
  - `tests.yml` — runs `pytest` on every push + PR (Python 3.14, ubuntu-latest).
  - `lint.yml` — runs `black --check princess tests` and `pylint princess tests`.
  - `openspec.yml` — runs `openspec validate --specs --strict` and `openspec validate <active changes> --strict`.
- **`openspec/config.yaml` upgrade** — fill in the empty scaffold with this project's actual context and rules:
  - `context:` — tech stack (Python 3.14, FastAPI, vanilla JS), house rules summary, license, the "use 'Princess', never 'shithead'" naming rule, WCAG AAA contrast requirement, 7-under-on-7 default.
  - `rules.tasks:` — atomic commit per task (each `- [x]` task closed should map to one commit); CI must be green before `/opsx:archive`.
  - `rules.proposal:` — docs (README, CHANGELOG) must be updated when surfaces change; a "Docs touched" line listed in Impact.

## Capabilities

### New Capabilities

- `repository-meta`: project distribution, documentation, CI, and contribution policy. Codifies what files must exist (README/CHANGELOG/CONTRIBUTING/LICENSE/NOTICE), what CI workflows must run on every PR, and the commit + docs-sync conventions for OpenSpec changes.

### Modified Capabilities

(none — this is a project-level addition, not a behavior change to any of the five existing capabilities)

## Impact

- **Affected code:** none of the runtime. All additions are top-level repo files (README, LICENSE already exists, NOTICE, CHANGELOG, CONTRIBUTING) and `.github/` directory.
- **Affected APIs:** none.
- **Affected dependencies:** none new at runtime; CI uses the existing `requirements-dev.txt`.
- **Affected systems:**
  - New `.git/` directory.
  - New remote at `github.com/<owner>/princess`.
  - GitHub Actions runs on push + PR.
- **Reversible:** repo can be deleted / made private from the GitHub UI. The local git history stays even if the remote goes.
- **Out of scope:** Dockerfile, deployment to a public URL, OAuth login, GitHub Pages site, conventional-commits enforcement (manual policy via CONTRIBUTING + reviewer for now).
