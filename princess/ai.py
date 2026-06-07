#!/usr/bin/env python3
"""
Simple heuristic AI for Princess Card Game.

Strategy:
- Always play from the active source (hand → face_up → face_down).
- Play the lowest legal rank, holding 2s (reset) and 10s (burn) for emergencies.
- If a same-rank card is on top, play multiples to burn via four-of-a-kind.
- If no legal play, use a 2 to escape, else 10 to burn, else pick up the pile.
- Face-down plays are blind — pick a random index.

Copyright 2026 Mike Huot

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from .cards import Card
from .game import BURN_CARD, Game, Player, Source, WILD_RESET


@dataclass
class AIDecision:
    action: str  # "play" or "pickup"
    source: Source | None = None
    indices: list[int] | None = None


def decide(game: Game, player: Player, *, rng: random.Random | None = None) -> AIDecision:
    rng = rng or random.Random()
    source = game.active_source(player)
    if source is None:
        return AIDecision(action="pickup")  # shouldn't happen — caller filters

    if source is Source.FACE_DOWN:
        idx = rng.randrange(len(player.face_down))
        return AIDecision(action="play", source=source, indices=[idx])

    cards: list[Card] = game._source_list(player, source)  # pylint: disable=protected-access
    legal = _choose_play(game, cards)
    if legal is not None:
        return AIDecision(action="play", source=source, indices=legal)
    return AIDecision(action="pickup")


def _choose_play(game: Game, cards: list[Card]) -> list[int] | None:
    by_rank: dict[int, list[int]] = {}
    for idx, card in enumerate(cards):
        if game.is_legal_rank(card.rank):
            by_rank.setdefault(card.rank, []).append(idx)
    if not by_rank:
        return None

    # Pile context for four-of-a-kind setup.
    top_rank = game.top_rank()
    top_run = _top_run_length(game)

    # 1) If we can complete a four-of-a-kind right now, do it.
    if top_rank is not None and top_rank in by_rank:
        needed = max(0, 4 - top_run)
        same = by_rank[top_rank]
        if needed and len(same) >= needed:
            return same[:needed]

    # 2) If we hold four of the same rank in hand, fire them.
    for rank, idxs in by_rank.items():
        if rank in (WILD_RESET, BURN_CARD):
            continue
        if len(idxs) >= 4:
            return idxs[:4]

    # 3) Otherwise: play the lowest non-special legal rank, one card.
    normal_ranks = sorted(r for r in by_rank if r not in (WILD_RESET, BURN_CARD))
    if normal_ranks:
        rank = normal_ranks[0]
        return [by_rank[rank][0]]

    # 4) Only specials left and we need to move — prefer burn (10), else reset (2).
    if BURN_CARD in by_rank:
        return [by_rank[BURN_CARD][0]]
    if WILD_RESET in by_rank:
        return [by_rank[WILD_RESET][0]]
    return None


def _top_run_length(game: Game) -> int:
    if not game.pile:
        return 0
    top_rank = game.pile[-1].rank
    run = 0
    for card in reversed(game.pile):
        if card.rank == top_rank:
            run += 1
        else:
            break
    return run
