## 1. Pre-conditions

- [x] 1.1 GitHub owner = `mhuot`. `gh auth status` confirmed.
- [x] 1.2 Visibility = `public`.
- [x] 1.3 First tag = `v0.1.0` (deferred until CI is green on `main`).
- [x] 1.4 Repo description = "A climbing-card game with a 7-under house rule — FastAPI backend, vanilla JS frontend." Topics: `card-game`, `climbing-cards`, `fastapi`, `websockets`, `python`, `apache-2`. **No "shithead" references in any GitHub-public surface.**

## 2. Local git init

- [x] 2.1 In the project root, run `git init -b main` (creates `.git/` with `main` as initial branch).
- [x] 2.2 Confirm `git config user.name = "Mike Huot"` and `git config user.email = "mhuot@mhuot.net"` (set locally if missing).
- [x] 2.3 Verify `.gitignore` already excludes `.venv`, `__pycache__`, `.pytest_cache`, `.DS_Store`. Add `logs/` to the ignore list defensively even though the runtime doesn't write files.

## 3. Docs

- [x] 3.1 Write `README.md` per the `Requirement: README is the front door` spec scenarios — tagline + emoji card art, 3-step quick start, status badges (placeholder URLs until CI runs once), feature list with 7-under callout, screenshot placeholder block, links to CONTRIBUTING / CHANGELOG / LICENSE / `openspec/`, "Princess only" naming policy note.
- [x] 3.2 Write `CONTRIBUTING.md` per the spec — dev setup with venv + `requirements-dev.txt`, `black` + `pylint` + `pytest` commands, OpenSpec workflow (`/opsx:propose` → `/opsx:apply` → `/opsx:archive`), commit-message format, PR checklist with docs reminder.
- [x] 3.3 Write `CHANGELOG.md` with the Keep-a-Changelog header, an empty `## [Unreleased]` section, then `## [0.1.0]` with bullets summarizing every capability shipped via the archived changes (`baseline`, `pickup-passes-turn`, `handle-human-exit-mid-game` — plus `show-last-three-moves` if it's been applied + archived by then).
- [x] 3.4 Write `NOTICE` (Apache 2.0 boilerplate naming the work and Mike Huot as copyright holder).
- [x] 3.5 Verify LICENSE already exists and is the unmodified Apache 2.0 text.

## 4. GitHub templates

- [x] 4.1 `.github/PULL_REQUEST_TEMPLATE.md` — Summary / Related OpenSpec change / Docs touched / Test plan sections.
- [x] 4.2 `.github/ISSUE_TEMPLATE/bug_report.md` — repro / expected / actual / environment / logs link.
- [x] 4.3 `.github/ISSUE_TEMPLATE/feature_request.md` — problem / proposal / alternatives.

## 5. GitHub Actions workflows

- [x] 5.1 `.github/workflows/tests.yml` — checkout, set up Python 3.14, `pip install -r requirements-dev.txt`, `pytest -q`. Runs on `push` to `main` and `pull_request`.
- [x] 5.2 `.github/workflows/lint.yml` — `black --check princess tests` and `pylint princess tests`. Same triggers.
- [x] 5.3 `.github/workflows/openspec.yml` — install `openspec` (if available via pip / Node) or use a curl-installed binary; run `openspec validate --specs --strict` then iterate any directories under `openspec/changes/` (excluding `archive/`) and run `openspec validate <name> --strict` for each.

## 6. OpenSpec config upgrade

- [x] 6.1 Replace the empty scaffold in `openspec/config.yaml` with a populated `context:` block: Python 3.14, FastAPI + WebSockets + vanilla JS, Apache 2.0 (Mike Huot), 7-under house rule (including 7-on-7 default), 2 wild / 10 burn / four-of-a-kind burn, WCAG AAA contrast, "Princess only" naming rule.
- [x] 6.2 Add `rules.tasks:` listing the "one commit per task" + "message `<change>: <task title>`" conventions.
- [x] 6.3 Add `rules.proposal:` requiring an Impact bullet for docs touched when user-visible surfaces change.

## 7. Local format + test pass

- [x] 7.1 Run `black princess tests` and commit any formatting diff.
- [x] 7.2 Run `pylint princess tests` and fix any new violations (none expected — the code is already pylint-clean per recent runs).
- [x] 7.3 Run `pytest -q` — expect green (105/105).
- [x] 7.4 Run `openspec validate --specs --strict` and `openspec validate establish-github-repo --strict`.

## 8. Initial commit + push

- [x] 8.1 `git add` the relevant files (not `.venv/`, not `__pycache__/`).
- [x] 8.2 Initial commit: `git commit -m "Initial Princess Card Game release (v0.1.0)"`. (This is the one exception to the per-task rule — the repo's birth.)
- [x] 8.3 `gh auth status` already shows `mhuot` as active (verified during propose).
- [x] 8.4 `gh repo create mhuot/princess --public --description "A climbing-card game with a 7-under house rule — FastAPI backend, vanilla JS frontend." --source=. --push`. Then `gh repo edit mhuot/princess --add-topic card-game --add-topic climbing-cards --add-topic fastapi --add-topic websockets --add-topic python --add-topic apache-2`.
- [x] 8.5 Confirm the push: `gh repo view mhuot/princess --web` (or just visit `https://github.com/mhuot/princess`).

## 9. CI shake-out

- [x] 9.1 Watch the first run of the three workflows. Expect at least one to fail (commonly `black --check` formatting drift).
- [x] 9.2 Fix anything that fails; commit per task; push.
- [x] 9.3 Once green, set branch protection in the GitHub UI requiring all three checks before merging into `main`.

## 10. Tag the release

- [x] 10.1 After CI is green on `main`, create the annotated tag: `git tag -a v0.1.0 -m "Initial Princess Card Game release"`.
- [x] 10.2 Push the tag: `git push origin v0.1.0`.
- [x] 10.3 Create a GitHub Release tied to the tag, body = the `## [0.1.0]` section from CHANGELOG.

## 11. Smoke

- [ ] 11.1 In a fresh `/tmp` directory: `gh repo clone <owner>/princess && cd princess && python3 -m venv .venv && .venv/bin/pip install -q -r requirements-dev.txt && .venv/bin/python -m pytest -q` — expect 105 passing.
- [ ] 11.2 `.venv/bin/python -m princess` and visit `http://127.0.0.1:8000`. Confirm a hand of Princess plays through against bots.
- [ ] 11.3 Add a real screenshot to the README replacing the placeholder block.
- [ ] 11.4 Optional: replace the badge placeholder URLs with the real shields.io URLs once CI has a run on `main`.

## 12. Wrap up

- [x] 12.1 Run `openspec status --change establish-github-repo` and confirm 4/4 artifacts done.
- [ ] 12.2 Archive via `/opsx:archive establish-github-repo` once everything is on GitHub and CI is green.
