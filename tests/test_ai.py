#!/usr/bin/env python3
"""
Tests for the AI heuristic.

Copyright 2026 Mike Huot

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0
"""

import random

from princess.ai import decide
from princess.cards import Card
from princess.game import Game, Player, Source


def _g(num=2):
    return Game([Player(f"p{i}", f"P{i}") for i in range(num)], seed=1)


def test_ai_plays_lowest_non_special_legal_card():
    game = _g()
    p = game.players[0]
    p.hand = [Card(10, "S"), Card(2, "H"), Card(5, "D"), Card(9, "C")]
    game.pile = [Card(4, "C")]
    game.current_idx = 0
    decision = decide(game, p, rng=random.Random(0))
    assert decision.action == "play"
    assert decision.source is Source.HAND
    chosen = [p.hand[i] for i in decision.indices]
    assert chosen[0].rank == 5


def test_ai_picks_up_when_no_legal_play():
    game = _g()
    p = game.players[0]
    p.hand = [Card(3, "S"), Card(4, "H")]
    game.pile = [Card(13, "C")]
    game.current_idx = 0
    decision = decide(game, p, rng=random.Random(0))
    assert decision.action == "pickup"


def test_ai_falls_back_to_burn_when_only_specials_legal():
    game = _g()
    p = game.players[0]
    p.hand = [Card(10, "S"), Card(2, "H")]
    game.pile = [Card(13, "C")]
    game.current_idx = 0
    decision = decide(game, p, rng=random.Random(0))
    assert decision.action == "play"
    chosen = [p.hand[i] for i in decision.indices]
    assert chosen[0].rank == 10  # prefer burn over reset


def test_ai_completes_four_of_a_kind_burn():
    game = _g()
    p = game.players[0]
    p.hand = [Card(6, "S"), Card(6, "H"), Card(9, "D")]
    game.pile = [Card(6, "C"), Card(6, "D")]
    game.current_idx = 0
    decision = decide(game, p, rng=random.Random(0))
    assert decision.action == "play"
    chosen = [p.hand[i] for i in decision.indices]
    assert {c.rank for c in chosen} == {6}
    assert len(chosen) == 2  # plays exactly enough to make four


def test_ai_obeys_reverse_rank_rule():
    # Default reverse rank is 5: 8 is illegal on a 5, 3 is the only legal hand card.
    game = _g()
    p = game.players[0]
    p.hand = [Card(8, "S"), Card(3, "H")]
    game.pile = [Card(5, "C")]
    game.current_idx = 0
    decision = decide(game, p, rng=random.Random(0))
    assert decision.action == "play"
    chosen = [p.hand[i] for i in decision.indices]
    assert chosen[0].rank == 3


def test_full_ai_vs_ai_game_terminates():
    """End-to-end smoke: two bots playing finishes in finite turns.

    Both the game's deal (via _g's fixed seed) and the AI's blind-pick RNG
    are seeded so this test is fully deterministic. With unseeded random,
    the AI vs AI loop occasionally exceeded 5000 iterations on CI.
    """
    game = _g()
    rng = random.Random(42)
    for _ in range(5000):
        if game.game_over:
            break
        p = game.current_player
        if not p.has_any_cards():
            break
        d = decide(game, p, rng=rng)
        if d.action == "pickup":
            game.pickup(p.pid)
        else:
            game.play(p.pid, d.source, d.indices)
    assert game.game_over, "AI vs AI game should terminate"
    assert len(game.finished_order) == 2
