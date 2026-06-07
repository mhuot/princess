#!/usr/bin/env python3
"""
Tests for the Princess Card Game rules engine.

Copyright 2026 Mike Huot

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0
"""

import pytest

from princess.cards import Card, make_deck
from princess.game import DEFAULT_REVERSE_RANK, Game, GameConfig, Player, Source


def fresh_game(num_players: int = 2, seed: int = 1) -> Game:
    players = [Player(pid=f"p{i}", name=f"Player {i}") for i in range(num_players)]
    return Game(players, seed=seed)


def rig(game: Game, *, idx: int, hand=None, face_up=None, face_down=None, pile=None, deck=None):
    """Force-set state for a scenario test."""
    player = game.players[idx]
    if hand is not None:
        player.hand = list(hand)
    if face_up is not None:
        player.face_up = list(face_up)
    if face_down is not None:
        player.face_down = list(face_down)
    if pile is not None:
        game.pile = list(pile)
    if deck is not None:
        game.deck = list(deck)
    game.current_idx = idx


def test_deck_has_52_unique_cards():
    deck = make_deck()
    assert len(deck) == 52
    assert len(set(deck)) == 52


def test_deal_gives_each_player_correct_counts():
    game = fresh_game(num_players=3, seed=42)
    for player in game.players:
        assert len(player.hand) == 3
        assert len(player.face_up) == 3
        assert len(player.face_down) == 3
    total_dealt = sum(9 for _ in game.players)
    assert len(game.deck) == 52 - total_dealt


def test_starter_avoids_2_and_10_when_picking_lowest():
    game = fresh_game(num_players=2, seed=7)
    game.players[0].hand = [Card(2, "S"), Card(13, "H"), Card(14, "D")]
    game.players[1].hand = [Card(4, "S"), Card(8, "H"), Card(9, "D")]
    game.current_idx = game._choose_starter()  # pylint: disable=protected-access
    assert game.current_idx == 1


def test_basic_legal_play_meets_or_exceeds_top():
    # Pile top 4 avoids triggering the default reverse rank (5).
    game = fresh_game()
    rig(game, idx=0, hand=[Card(8, "S")], pile=[Card(4, "C")])
    result = game.play("p0", Source.HAND, [0])
    assert result.ok, result.error
    assert game.pile[-1].rank == 8


def test_lower_card_is_illegal():
    game = fresh_game()
    rig(game, idx=0, hand=[Card(3, "S")], pile=[Card(8, "C")])
    result = game.play("p0", Source.HAND, [0])
    assert not result.ok
    assert "illegal" in result.error


def test_reverse_rank_forces_next_play_under_default_5():
    game = fresh_game()
    rig(game, idx=0, hand=[Card(8, "S")], pile=[Card(5, "C")])
    result = game.play("p0", Source.HAND, [0])
    assert not result.ok, "8 should be illegal after the default reverse rank 5"


def test_reverse_rank_allows_lower_cards():
    game = fresh_game()
    rig(game, idx=0, hand=[Card(3, "S")], pile=[Card(5, "C")])
    result = game.play("p0", Source.HAND, [0])
    assert result.ok


def test_burn_legal_over_reverse_rank():
    game = fresh_game()
    rig(game, idx=0, hand=[Card(10, "S")], pile=[Card(5, "C")])
    result = game.play("p0", Source.HAND, [0])
    assert result.ok
    assert result.burned
    assert result.same_player_again
    assert game.pile == []


def test_reset_legal_over_reverse_rank():
    game = fresh_game()
    rig(game, idx=0, hand=[Card(2, "S")], pile=[Card(5, "C")])
    result = game.play("p0", Source.HAND, [0])
    assert result.ok
    assert game.top_rank() == 2


@pytest.mark.parametrize("top_rank", [None, 5, 7, 13, 14])
def test_reverse_rank_is_wild(top_rank):
    """The reverse rank (default 5) is always legal regardless of pile top."""
    game = fresh_game()
    pile = [Card(top_rank, "C")] if top_rank is not None else []
    rig(game, idx=0, hand=[Card(5, "H")], pile=pile)
    result = game.play("p0", Source.HAND, [0])
    assert result.ok, f"5 should be legal on pile_top={top_rank}"
    assert game.top_rank() == 5


@pytest.mark.parametrize(
    "reverse,top,attempt,expected_ok",
    [
        (4, 4, 3, True),  # under 4: 3 is legal
        (4, 4, 5, False),  # on a 4 (under-4 active), 5 ≥ 4 fails under-rule and 5 isn't wild here
        (9, 9, 8, True),  # under 9: 8 is legal
        (9, 9, 10, True),  # 10 always legal (burn)
        (13, 13, 12, True),  # under K: Q is legal
        (
            13,
            13,
            14,
            False,
        ),  # A on K (under-K active): A is not wild and ≥ rule doesn't bypass under-rule
        (14, 14, 13, True),  # under A: K is legal
        (14, 14, 14, True),  # reverse rank itself is wild → A on A legal
    ],
)
def test_reverse_rank_configurable(reverse, top, attempt, expected_ok):
    game = fresh_game(num_players=2)
    game.config = GameConfig(reverse_rank=reverse)
    rig(game, idx=0, hand=[Card(attempt, "S")], pile=[Card(top, "C")])
    result = game.play("p0", Source.HAND, [0])
    assert result.ok is expected_ok


def test_reverse_rank_invalid_coerces_to_default():
    cfg = GameConfig.from_dict({"reverse_rank": 10})  # 10 is wild, not legal
    assert cfg.reverse_rank == DEFAULT_REVERSE_RANK
    assert not hasattr(cfg, "same_on_reverse")


def test_legacy_keys_ignored():
    """Both legacy keys (seven_on_seven, same_on_reverse) are silently dropped."""
    cfg = GameConfig.from_dict(
        {
            "reverse_rank": 7,
            "same_on_reverse": False,
            "seven_on_seven": False,
        }
    )
    assert cfg.reverse_rank == 7
    assert not hasattr(cfg, "same_on_reverse")


def test_2_acts_as_reset_for_next_play():
    game = fresh_game()
    rig(game, idx=0, hand=[Card(2, "S"), Card(3, "H")], pile=[Card(13, "C")])
    result = game.play("p0", Source.HAND, [0])
    assert result.ok
    assert not result.same_player_again  # 2 does NOT replay
    # Now top is 2 — anything is legal.
    assert game.is_legal_rank(3)
    assert game.is_legal_rank(14)


def test_10_burns_pile_and_replays():
    game = fresh_game()
    rig(game, idx=0, hand=[Card(10, "S"), Card(4, "H")], pile=[Card(5, "C")])
    result = game.play("p0", Source.HAND, [0])
    assert result.ok
    assert result.burned
    assert result.same_player_again
    assert game.pile == []
    assert game.current_player.pid == "p0"


def test_four_of_a_kind_in_single_play_burns():
    game = fresh_game()
    rig(
        game,
        idx=0,
        hand=[Card(8, "S"), Card(8, "H"), Card(8, "D"), Card(8, "C")],
        pile=[Card(4, "C")],
    )
    result = game.play("p0", Source.HAND, [0, 1, 2, 3])
    assert result.ok
    assert result.burned
    assert game.pile == []


def test_four_of_a_kind_across_plays_burns():
    game = fresh_game(num_players=2)
    rig(game, idx=0, hand=[Card(6, "S")], pile=[Card(6, "C"), Card(6, "D"), Card(6, "H")])
    result = game.play("p0", Source.HAND, [0])
    assert result.ok
    assert result.burned


def test_multi_card_play_requires_same_rank():
    game = fresh_game()
    rig(game, idx=0, hand=[Card(8, "S"), Card(9, "H")], pile=[Card(5, "C")])
    result = game.play("p0", Source.HAND, [0, 1])
    assert not result.ok


def test_pickup_pile_into_hand():
    game = fresh_game()
    rig(
        game,
        idx=0,
        hand=[Card(3, "S")],
        pile=[Card(13, "C"), Card(13, "D")],
    )
    result = game.pickup("p0")
    assert result.ok
    assert game.pile == []
    assert {c.rank for c in game.players[0].hand} == {3, 13}
    assert game.current_idx == 1


def test_hand_refills_from_deck_after_play():
    game = fresh_game()
    rig(
        game,
        idx=0,
        hand=[Card(8, "S")],
        pile=[Card(4, "C")],
        deck=[Card(11, "S"), Card(12, "H"), Card(13, "D")],
    )
    result = game.play("p0", Source.HAND, [0])
    assert result.ok
    assert len(game.players[0].hand) == 3


def test_no_refill_when_deck_empty():
    game = fresh_game()
    rig(game, idx=0, hand=[Card(8, "S")], pile=[Card(4, "C")], deck=[])
    result = game.play("p0", Source.HAND, [0])
    assert result.ok
    assert game.players[0].hand == []


def test_transition_to_face_up_when_hand_and_deck_empty():
    game = fresh_game()
    rig(
        game,
        idx=0,
        hand=[],
        face_up=[Card(8, "S")],
        face_down=[Card(3, "S"), Card(4, "H"), Card(5, "D")],
        pile=[Card(4, "C")],
        deck=[],
    )
    assert game.active_source(game.players[0]) is Source.FACE_UP
    result = game.play("p0", Source.FACE_UP, [0])
    assert result.ok


def test_face_down_legal_play_succeeds():
    game = fresh_game()
    rig(
        game,
        idx=0,
        hand=[],
        face_up=[],
        face_down=[Card(8, "S")],
        pile=[Card(5, "C")],
        deck=[],
    )
    result = game.play("p0", Source.FACE_DOWN, [0])
    assert result.ok
    assert result.revealed == Card(8, "S")


def test_face_down_illegal_play_picks_up_pile_plus_card():
    game = fresh_game(num_players=2)
    rig(
        game,
        idx=0,
        hand=[],
        face_up=[],
        face_down=[Card(3, "S")],
        pile=[Card(13, "C"), Card(13, "D")],
        deck=[],
    )
    result = game.play("p0", Source.FACE_DOWN, [0])
    assert result.ok
    assert result.picked_up
    assert result.revealed == Card(3, "S")
    assert game.players[0].hand == [Card(13, "C"), Card(13, "D"), Card(3, "S")]
    assert game.pile == []


def test_player_finishes_when_all_cards_played():
    game = fresh_game(num_players=2)
    rig(
        game,
        idx=0,
        hand=[],
        face_up=[],
        face_down=[Card(10, "S")],  # legal burn
        pile=[Card(5, "C")],
        deck=[],
    )
    result = game.play("p0", Source.FACE_DOWN, [0])
    assert result.ok
    assert game.players[0].finished
    assert "p0" in game.finished_order
    # Game over: only p1 left.
    assert game.game_over


def test_game_continues_with_three_players_when_one_finishes():
    game = fresh_game(num_players=3)
    rig(
        game,
        idx=0,
        hand=[],
        face_up=[],
        face_down=[Card(10, "S")],
        pile=[Card(5, "C")],
        deck=[],
    )
    result = game.play("p0", Source.FACE_DOWN, [0])
    assert result.ok
    assert not game.game_over
    assert game.current_player.pid in ("p1", "p2")


def test_cannot_play_out_of_turn():
    game = fresh_game()
    rig(game, idx=0, hand=[Card(8, "S")], pile=[Card(5, "C")])
    result = game.play("p1", Source.HAND, [0])
    assert not result.ok
    assert "turn" in result.error


def test_must_use_active_source():
    game = fresh_game()
    rig(
        game,
        idx=0,
        hand=[Card(8, "S")],
        face_up=[Card(9, "H")],
        pile=[Card(5, "C")],
    )
    result = game.play("p0", Source.FACE_UP, [0])
    assert not result.ok


def test_view_for_hides_other_players_hands():
    game = fresh_game(num_players=2)
    view = game.view_for("p0")
    assert "hand" in view["you"]
    for p_view in view["players"]:
        assert "hand" not in p_view  # only counts exposed
        assert "hand_count" in p_view


def test_under_reverse_active_flag_in_view():
    game = fresh_game()
    rig(game, idx=0, hand=[Card(3, "S")], pile=[Card(5, "C")])
    view = game.view_for("p0")
    assert view["under_reverse"] is True
    # Legacy alias preserved for one release.
    assert view["under_seven"] is True


def test_invalid_input_rejected():
    game = fresh_game()
    rig(game, idx=0, hand=[Card(8, "S")], pile=[Card(5, "C")])
    bad = game.play("p0", Source.HAND, [])
    assert not bad.ok
    bad = game.play("p0", Source.HAND, [5])
    assert not bad.ok
    bad = game.play("p0", Source.HAND, [0, 0])
    assert not bad.ok


def test_pickup_rejected_when_pile_empty():
    game = fresh_game()
    rig(game, idx=0, hand=[Card(8, "S")], pile=[])
    assert not game.pickup("p0").ok


def test_burn_after_finishing_does_not_replay_finished_player():
    game = fresh_game(num_players=3)
    rig(
        game,
        idx=0,
        hand=[Card(10, "S")],
        face_up=[],
        face_down=[],
        pile=[Card(5, "C")],
        deck=[],
    )
    result = game.play("p0", Source.HAND, [0])
    assert result.ok
    assert game.players[0].finished
    assert not result.same_player_again
    assert not game.game_over
    assert game.current_player.pid in ("p1", "p2")


@pytest.mark.parametrize("rank", [2, 10])
def test_special_cards_legal_on_empty_pile(rank):
    game = fresh_game()
    rig(game, idx=0, hand=[Card(rank, "S")], pile=[])
    assert game.play("p0", Source.HAND, [0]).ok


# --- Swap-phase tests --------------------------------------------------------


def _swap_game(num_players: int = 2, seed: int = 1) -> Game:
    players = [Player(pid=f"p{i}", name=f"Player {i}") for i in range(num_players)]
    return Game(players, seed=seed, swap_phase=True)


def test_swap_phase_starts_in_setup_with_choose_pile():
    game = _swap_game(num_players=3)
    assert game.phase == "setup"
    for player in game.players:
        assert len(player.face_down) == 3
        assert len(player.choose) == 6
        assert player.hand == []
        assert player.face_up == []
        assert not player.ready


def test_play_rejected_during_setup_phase():
    game = _swap_game()
    result = game.play("p0", Source.HAND, [0])
    assert not result.ok
    assert "setting up" in result.error


def test_pickup_rejected_during_setup_phase():
    game = _swap_game()
    game.pile = [Card(8, "S")]  # synthetic; we never reach this state in practice
    result = game.pickup("p0")
    assert not result.ok
    assert "setting up" in result.error


def test_set_face_up_locks_three_into_face_up_and_three_into_hand():
    game = _swap_game()
    before = list(game.players[0].choose)
    result = game.set_face_up("p0", [0, 2, 4])
    assert result.ok
    p0 = game.players[0]
    assert p0.face_up == [before[0], before[2], before[4]]
    assert p0.hand == [before[1], before[3], before[5]]
    assert p0.choose == []
    assert p0.ready


def test_set_face_up_rejects_wrong_count():
    game = _swap_game()
    bad_short = game.set_face_up("p0", [0, 1])
    assert not bad_short.ok
    bad_long = game.set_face_up("p0", [0, 1, 2, 3])
    assert not bad_long.ok


def test_set_face_up_rejects_duplicate_indices():
    game = _swap_game()
    result = game.set_face_up("p0", [0, 0, 1])
    assert not result.ok


def test_set_face_up_rejects_out_of_range_indices():
    game = _swap_game()
    result = game.set_face_up("p0", [0, 1, 99])
    assert not result.ok


def test_set_face_up_rejects_already_ready_player():
    game = _swap_game()
    assert game.set_face_up("p0", [0, 1, 2]).ok
    again = game.set_face_up("p0", [3, 4, 5])
    assert not again.ok
    assert "locked in" in again.error


def test_phase_transitions_to_playing_when_all_ready():
    game = _swap_game(num_players=2)
    game.set_face_up("p0", [0, 1, 2])
    assert game.phase == "setup"
    game.set_face_up("p1", [3, 4, 5])
    assert game.phase == "playing"
    # Current player must be one of the seats now.
    assert game.current_player.pid in ("p0", "p1")


def test_set_face_up_rejected_after_phase_is_playing():
    game = _swap_game()
    game.set_face_up("p0", [0, 1, 2])
    game.set_face_up("p1", [0, 1, 2])
    assert game.phase == "playing"
    result = game.set_face_up("p0", [0, 1, 2])
    assert not result.ok
    assert "not in setup phase" in result.error


# --- Pickup-passes-turn regression tests -------------------------------------


def test_pickup_advances_to_next_player_two_player():
    """Voluntary pickup ends the picker's turn — see game-engine spec."""
    game = fresh_game(num_players=2)
    rig(
        game,
        idx=0,
        hand=[Card(3, "S")],
        pile=[Card(13, "C"), Card(13, "D")],
    )
    assert game.current_idx == 0
    result = game.pickup("p0")
    assert result.ok
    assert game.pile == []
    assert game.current_idx == 1
    assert game.current_player.pid == "p1"


def test_face_down_illegal_pickup_advances_turn():
    """Illegal face-down reveal forces pickup AND passes the turn."""
    game = fresh_game(num_players=2)
    rig(
        game,
        idx=0,
        hand=[],
        face_up=[],
        face_down=[Card(3, "S")],
        pile=[Card(13, "C"), Card(13, "D")],
        deck=[],
    )
    result = game.play("p0", Source.FACE_DOWN, [0])
    assert result.ok
    assert result.picked_up
    assert game.current_player.pid == "p1"


def test_pickup_skips_finished_player():
    """Pickup advances to the next NON-finished player."""
    game = fresh_game(num_players=3)
    rig(
        game,
        idx=0,
        hand=[Card(3, "S")],
        pile=[Card(13, "C")],
    )
    game.players[1].finished = True  # p1 is already out
    result = game.pickup("p0")
    assert result.ok
    assert game.current_player.pid == "p2"


def test_last_actions_starts_empty_then_records_deal_complete():
    game = _swap_game(num_players=2)
    assert game.last_actions == []
    game.set_face_up("p0", [0, 1, 2])
    assert game.last_actions == []  # only deal-complete is recorded
    game.set_face_up("p1", [0, 1, 2])
    assert len(game.last_actions) == 1
    assert game.last_actions[0]["text"] == "deal complete — game on!"


def test_last_actions_caps_at_three():
    game = fresh_game(num_players=2)
    rig(game, idx=0, hand=[Card(5, "S")], pile=[Card(4, "C")], deck=[])
    game.play("p0", Source.HAND, [0])  # 5 on 4
    # Now p1's turn. Loop through several pickups by both sides to grow history.
    rig(game, idx=1, hand=[Card(3, "H")], pile=[Card(13, "D")], deck=[])
    game.pickup("p1")
    rig(game, idx=0, hand=[Card(3, "S")], pile=[Card(13, "C")], deck=[])
    game.pickup("p0")
    rig(game, idx=1, hand=[Card(3, "D")], pile=[Card(13, "H")], deck=[])
    game.pickup("p1")
    assert len(game.last_actions) == 3
    # The earliest "played 5S" should have been evicted.
    assert all("played 5S" not in entry["text"] for entry in game.last_actions)


def test_last_actions_burn_flag_on_ten():
    game = fresh_game()
    rig(game, idx=0, hand=[Card(10, "S")], pile=[Card(5, "C")], deck=[])
    result = game.play("p0", Source.HAND, [0])
    assert result.ok and result.burned
    newest = game.last_actions[-1]
    assert newest["burned"] is True
    assert newest["picked_up"] is False


def test_last_actions_burn_flag_on_four_of_a_kind():
    game = fresh_game(num_players=2)
    rig(
        game,
        idx=0,
        hand=[Card(6, "S")],
        pile=[Card(6, "C"), Card(6, "D"), Card(6, "H")],
        deck=[],
    )
    game.play("p0", Source.HAND, [0])
    assert game.last_actions[-1]["burned"] is True


def test_last_actions_pickup_flag_voluntary():
    game = fresh_game(num_players=2)
    rig(game, idx=0, hand=[Card(3, "S")], pile=[Card(13, "C")], deck=[])
    game.pickup("p0")
    newest = game.last_actions[-1]
    assert newest["picked_up"] is True
    assert newest["burned"] is False
    assert newest["actor_pid"] == "p0"


def test_last_actions_pickup_flag_face_down_illegal():
    game = fresh_game(num_players=2)
    rig(
        game,
        idx=0,
        hand=[],
        face_up=[],
        face_down=[Card(3, "S")],
        pile=[Card(13, "C"), Card(13, "D")],
        deck=[],
    )
    game.play("p0", Source.FACE_DOWN, [0])
    assert game.last_actions[-1]["picked_up"] is True


def test_last_actions_finished_pid_set():
    game = fresh_game(num_players=2)
    rig(
        game,
        idx=0,
        hand=[Card(10, "S")],
        face_up=[],
        face_down=[],
        pile=[Card(5, "C")],
        deck=[],
    )
    # p0 plays their last card and finishes.
    result = game.play("p0", Source.HAND, [0])
    assert result.ok
    assert game.players[0].finished
    assert game.last_actions[-1]["finished_pid"] == "p0"


def test_last_action_legacy_key_matches_newest_text():
    game = fresh_game()
    rig(game, idx=0, hand=[Card(8, "S")], pile=[Card(4, "C")], deck=[])
    game.play("p0", Source.HAND, [0])
    state = game.public_state()
    assert state["last_action"] == state["last_actions"][-1]["text"]
    assert "played 8S" in state["last_action"]


def test_end_round_ranks_by_hand_size():
    game = fresh_game(num_players=3)
    rig(game, idx=0, hand=[Card(3, "S")], face_up=[], face_down=[])
    rig(game, idx=1, hand=[Card(4, "S"), Card(5, "S")], face_up=[Card(6, "H")], face_down=[])
    rig(game, idx=2, hand=[], face_up=[Card(7, "C")], face_down=[Card(8, "D")])
    result = game.end_round()
    assert result.ok
    assert game.game_over
    assert game.finished_order == ["p0", "p2", "p1"]


def test_end_round_no_op_when_game_over():
    game = fresh_game(num_players=2)
    game.game_over = True
    result = game.end_round()
    assert not result.ok
    assert "already over" in result.error


def test_last_action_empty_when_no_history():
    # Swap-phase game before anyone locks in has no recorded actions.
    game = _swap_game(num_players=2)
    state = game.public_state()
    assert state["last_actions"] == []
    assert state["last_action"] == ""


def test_pickup_called_for_bot_pid_advances_turn():
    """Force-pickup fallback path: when the engine rejects a bot's play, the
    server calls game.pickup(bot.pid). That route MUST end the bot's turn."""
    game = fresh_game(num_players=2)
    rig(
        game,
        idx=0,
        hand=[Card(4, "H")],
        pile=[Card(9, "S"), Card(9, "D")],
    )
    # p0 is acting as a "bot" for this scenario — the engine doesn't care.
    result = game.pickup("p0")
    assert result.ok
    assert game.current_player.pid == "p1"
