# 👑 Princess Card Game

> _A climbing-card game with a 7-under house rule._
> _Built in an afternoon. Plays for hours._

```
   ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐
   │A♠   │  │K♥   │  │7♦   │  │2♣   │
   │  ♛  │  │  ♛  │  │  ♛  │  │  ♛  │
   │   A │  │   K │  │   7 │  │   2 │
   └─────┘  └─────┘  └─────┘  └─────┘
            climb · burn · reset · reverse
```

[![Tests](https://github.com/mhuot/princess/actions/workflows/tests.yml/badge.svg)](https://github.com/mhuot/princess/actions/workflows/tests.yml)
[![Lint](https://github.com/mhuot/princess/actions/workflows/lint.yml/badge.svg)](https://github.com/mhuot/princess/actions/workflows/lint.yml)
[![OpenSpec](https://github.com/mhuot/princess/actions/workflows/openspec.yml/badge.svg)](https://github.com/mhuot/princess/actions/workflows/openspec.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.14](https://img.shields.io/badge/python-3.14-blue.svg)](https://www.python.org/downloads/)

## Quick start

```bash
git clone https://github.com/mhuot/princess.git
cd princess && python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m princess
```

Open <http://127.0.0.1:8000>, enter a name, click **Create new room**, click **Add bot** (they have *opinions* about your skill), and click **Start game**. That's it.

> Need a screenshot? Add one to `docs/screenshot.png` — see [Contributing](CONTRIBUTING.md#screenshots).

## The 7-under house rule

This is the one rule that makes Princess Princess.

> **When the top of the discard pile is a 7, the next card must be UNDER 7.**

So `7 → 6`, `7 → 4`, `7 → 2` are all legal. `7 → 8` is not. Two specials still work:

- **10** is always legal — it burns the pile and you go again.
- **2** is always legal — it resets the pile to "anything goes."

And by default, the **7 itself is legal on a 7** (toggleable in the house-rules panel).

## Features

- **2–4 player rooms over the internet.** Share a 4-character room code, your friends join from their browser. WebSocket-driven, FastAPI backend, vanilla JS frontend — no build step.
- **Play solo against AI.** A heuristic bot picks lowest legal, hoards 2s and 10s, completes four-of-a-kind burns when it can.
- **100 random bot names that roast you.** *Skill Issue*, *Cope Dispenser*, *Mid Bot Maxine*, *Mensa Queen*, *Diff Lord*, …
- **Quit modal with options.** Take over with a bot (round continues without you), end the round (winner banner with current standings), or abort to lobby.
- **Pre-game swap phase.** Dealt 3 face-down + 6 to choose from; pick 3 to go face-up, 3 stay in hand. Bots auto-pick their highest.
- **WCAG AAA color palette.** ≥7:1 contrast, skip link, keyboard-visible focus rings, `prefers-reduced-motion` respect.
- **In-browser log viewer at `/logs`.** Live-tail with auto-refresh, download as text, clear button. No filesystem footprint — bounded 2000-entry ring buffer.
- **Tested.** 105 unit + integration tests covering the engine, AI, server, log buffer, room lifecycle, and the WebSocket round-trip.
- **Spec-driven.** Every behavior is documented in [`openspec/specs/`](openspec/specs/) — game-engine, ai-bot, room-server, web-frontend, logging, repository-meta.

## Project layout

```
princess/
├── princess/            # Python server + engine
│   ├── game.py          #   pure-Python rules engine
│   ├── ai.py            #   heuristic bot
│   ├── rooms.py         #   in-memory room registry, bot loop
│   ├── server.py        #   FastAPI HTTP + WebSockets
│   ├── bot_names.py     #   100-name roster
│   └── logging_config.py#   in-memory FIFO + handler
├── static/              # Vanilla JS / CSS / HTML
│   ├── index.html
│   ├── app.js
│   ├── styles.css
│   └── logs.html
├── tests/               # 105 pytest tests
├── openspec/            # Spec set + change history
│   ├── specs/           #   6 capability specs
│   └── changes/archive/ #   completed proposals
├── CONTRIBUTING.md      # dev setup, OpenSpec workflow, PR checklist
├── CHANGELOG.md         # Keep a Changelog format
├── LICENSE              # Apache 2.0
└── NOTICE               # attribution
```

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). The short version:

1. Fork & clone.
2. `python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt`.
3. `black princess tests && pylint princess tests && pytest -q`.
4. For any non-trivial change, open an OpenSpec proposal first — see the [`openspec/`](openspec/) directory and the workflow in CONTRIBUTING.

## House naming policy

This project is called **Princess**. In all code, UI copy, commit messages, and public-facing surfaces (including GitHub topics and descriptions), the inspiring game's vulgar name is **never used**. Private design notes can mention the family of games (Shithead/Karma) for context; everything else stays Princess. Reviewers enforce.

## License

Apache License 2.0 — see [`LICENSE`](LICENSE). Copyright © 2026 Mike Huot.

A `NOTICE` file accompanies redistributions per Section 4(d) of the license.
