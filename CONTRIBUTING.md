# Contributing to Princess

Thanks for poking around — this guide is short and practical.

## Dev setup

```bash
git clone https://github.com/mhuot/princess.git
cd princess
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
```

Confirm everything works:

```bash
.venv/bin/black --check princess tests
.venv/bin/pylint princess tests
.venv/bin/python -m pytest -q
.venv/bin/python -m princess          # http://127.0.0.1:8000
```

All four should be green out of the gate. If `black --check` fails on a fresh clone, open an issue — that's a CI gap.

## The four commands you'll use

| Command | What it does |
| --- | --- |
| `black princess tests` | Reformat in place. Run before committing. |
| `pylint princess tests` | Lint. Should report `10/10`. |
| `pytest -q` | Run the test suite. Should report `105 passed`. |
| `python -m princess` | Boot the server at <http://127.0.0.1:8000>. |

Hint: `pytest -k <keyword>` filters by test name; `-x` stops on first failure.

## How we work: OpenSpec

Princess uses [OpenSpec](https://openspec.dev) — a tiny spec-driven workflow. **Every non-trivial change starts with a proposal.** Trivial changes (typo fixes, version bumps) can skip it.

```
/opsx:propose "add reconnection by pid"
        # author creates proposal.md, design.md, specs/*.md, tasks.md
/opsx:apply <change-name>
        # author works through tasks one commit at a time
/opsx:archive <change-name>
        # specs synced into openspec/specs/, change moved to archive/
```

You can see every shipped change under [`openspec/changes/archive/`](openspec/changes/archive/). The live spec set is in [`openspec/specs/`](openspec/specs/).

### One commit per task

When implementing a change, **each `- [x]` task in `tasks.md` closes with one commit**. Commit-message format:

```
<change-name>: <task title>
```

Examples:

```
handle-human-exit-mid-game: Add Game.end_round helper
handle-human-exit-mid-game: Wire up quit modal
```

The initial repo creation commit is the one exception (`Initial Princess Card Game release (v0.1.0)`).

This convention is encoded in [`openspec/config.yaml`](openspec/config.yaml) — future agents pick it up automatically.

## Docs stay in sync with code

If your change touches a **user-visible surface** (UI behavior, REST endpoint, config flag, log format), the same change must update:

- `README.md` — when the feature list, quick-start, or rule description changes.
- `CHANGELOG.md` — append a bullet to the `## [Unreleased]` section.

PR reviewers check this. Behavior changes without doc updates get a `needs-docs` label.

## PR checklist

Copy-paste this into your PR body (the template will pre-populate it):

- [ ] All four commands above run clean.
- [ ] OpenSpec change linked in PR description.
- [ ] If user-visible surfaces changed, README + CHANGELOG updated.
- [ ] No references to the inspiring game's name in code/UI/commits (Princess only — see [README § House naming policy](README.md#house-naming-policy)).
- [ ] Tests cover the new behavior (unit and/or integration).

## Screenshots

If you change a visible UI surface and have time, drop an updated screenshot to `docs/screenshot.png`. The README references it. Optimize PNGs through `pngcrush` or similar before committing.

## Style notes

- **Python**: PEP 8, `black` line length 100, `pylint` clean (`10/10`).
- **JavaScript**: Vanilla ES2020. No bundler, no framework. Functions over classes; flat state object in `static/app.js`.
- **CSS**: Hand-rolled, WCAG AAA contrast (≥7:1 normal text). No frameworks.
- **Apache 2.0 headers**: Every new `.py` file under `princess/` or `tests/` gets the standard header — copy from any existing file.
- **Comments**: Default to none. Add only when *why* isn't obvious from the code.

## Code of conduct

Be kind, don't be a jerk. We're playing cards.
