#!/usr/bin/env python3
"""
Princess Card Game rules engine.

Princess Card Game rules:
- 7 forces next play to be UNDER 7 (treats 7 as a "reverse" card)
- 2 is a reset (anything can be played next; always legal)
- 10 burns the pile and the same player plays again (always legal)
- Four-of-a-kind on the top of the pile burns it and same player plays again

The engine is pure-Python and headless — drive it from the server or tests.

Copyright 2026 Mike Huot

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass, field
from enum import Enum

from .cards import Card, make_deck

HAND_SIZE = 3
FACE_UP_COUNT = 3
FACE_DOWN_COUNT = 3
WILD_RESET = 2
BURN_CARD = 10
LAST_ACTIONS_CAP = 3
DEFAULT_REVERSE_RANK = 5
# Legal reverse ranks exclude the wild cards (2 reset, 10 burn).
LEGAL_REVERSE_RANKS = frozenset({3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14})


@dataclass
class GameConfig:
    """Per-room rule toggles. Defaults match the house variant.

    The reverse rank is the rank that, when on top of the pile, forces the
    next play to be UNDER it. Default 5 (the project's house rule). The
    rank itself can also be played onto itself when ``same_on_reverse``
    is true (the default).
    """

    reverse_rank: int = DEFAULT_REVERSE_RANK
    same_on_reverse: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict | None) -> "GameConfig":
        if not data:
            return cls()
        kwargs: dict = {}
        if "reverse_rank" in data:
            try:
                rank = int(data["reverse_rank"])
            except (TypeError, ValueError):
                rank = DEFAULT_REVERSE_RANK
            if rank not in LEGAL_REVERSE_RANKS:
                rank = DEFAULT_REVERSE_RANK
            kwargs["reverse_rank"] = rank
        if "same_on_reverse" in data:
            kwargs["same_on_reverse"] = bool(data["same_on_reverse"])
        return cls(**kwargs)


class Source(str, Enum):
    HAND = "hand"
    FACE_UP = "face_up"
    FACE_DOWN = "face_down"


@dataclass
class Player:
    pid: str
    name: str
    hand: list[Card] = field(default_factory=list)
    face_up: list[Card] = field(default_factory=list)
    face_down: list[Card] = field(default_factory=list)
    choose: list[Card] = field(default_factory=list)
    finished: bool = False
    ready: bool = False

    def has_any_cards(self) -> bool:
        return bool(self.hand or self.face_up or self.face_down)


@dataclass
class PlayResult:
    ok: bool
    error: str | None = None
    burned: bool = False
    picked_up: bool = False
    revealed: Card | None = None
    same_player_again: bool = False
    finished_pid: str | None = None
    game_over: bool = False


class Game:
    """Headless game state for Princess Card Game."""

    def __init__(
        self,
        players: list[Player],
        *,
        seed: int | None = None,
        swap_phase: bool = False,
        config: GameConfig | None = None,
    ):
        if not 2 <= len(players) <= 4:
            raise ValueError("Princess Card Game supports 2–4 players")
        self.players = players
        self.config = config or GameConfig()
        self.deck: list[Card] = []
        self.pile: list[Card] = []
        self.current_idx: int = 0
        self.finished_order: list[str] = []
        self.game_over: bool = False
        self.phase: str = "setup" if swap_phase else "playing"
        self.last_actions: list[dict] = []
        self._rng = random.Random(seed)
        if swap_phase:
            self._deal_with_swap()
        else:
            self._deal()
            self._record("game started")

    # ---- setup -----------------------------------------------------------

    def _deal(self) -> None:
        deck = make_deck()
        self._rng.shuffle(deck)
        for player in self.players:
            player.face_down = [deck.pop() for _ in range(FACE_DOWN_COUNT)]
            player.face_up = [deck.pop() for _ in range(FACE_UP_COUNT)]
            player.hand = [deck.pop() for _ in range(HAND_SIZE)]
            player.ready = True
        self.deck = deck
        self.current_idx = self._choose_starter()

    def _deal_with_swap(self) -> None:
        """Deal 3 face-down + 6 cards into 'choose' for each player to pick from."""
        deck = make_deck()
        self._rng.shuffle(deck)
        choose_size = FACE_UP_COUNT + HAND_SIZE
        for player in self.players:
            player.face_down = [deck.pop() for _ in range(FACE_DOWN_COUNT)]
            player.choose = [deck.pop() for _ in range(choose_size)]
            player.hand = []
            player.face_up = []
            player.ready = False
        self.deck = deck

    def set_face_up(self, pid: str, indices: list[int]) -> PlayResult:
        """During the setup phase, player picks FACE_UP_COUNT cards from their choose pile."""
        if self.phase != "setup":
            return PlayResult(ok=False, error="not in setup phase")
        player = self.player(pid)
        if player.ready:
            return PlayResult(ok=False, error="already locked in")
        if len(indices) != FACE_UP_COUNT or len(set(indices)) != FACE_UP_COUNT:
            return PlayResult(ok=False, error=f"select exactly {FACE_UP_COUNT} distinct cards")
        if any(i < 0 or i >= len(player.choose) for i in indices):
            return PlayResult(ok=False, error="card index out of range")
        idx_set = set(indices)
        player.face_up = [player.choose[i] for i in sorted(indices)]
        player.hand = [c for i, c in enumerate(player.choose) if i not in idx_set]
        player.choose = []
        player.ready = True
        if all(p.ready for p in self.players):
            self.phase = "playing"
            self.current_idx = self._choose_starter()
            self._record("deal complete — game on!")
        return PlayResult(ok=True)

    def _choose_starter(self) -> int:
        """Lowest hand card (excluding 2s and 10s) starts. Ties: lowest index."""
        best_idx = 0
        best_rank = 99
        for idx, player in enumerate(self.players):
            for card in player.hand:
                if card.rank in (WILD_RESET, BURN_CARD):
                    continue
                if card.rank < best_rank:
                    best_rank = card.rank
                    best_idx = idx
        return best_idx

    # ---- accessors -------------------------------------------------------

    def player(self, pid: str) -> Player:
        for player in self.players:
            if player.pid == pid:
                return player
        raise KeyError(pid)

    @property
    def current_player(self) -> Player:
        return self.players[self.current_idx]

    def active_source(self, player: Player) -> Source | None:
        """The source a player must currently play from. None if finished."""
        if player.hand:
            return Source.HAND
        if player.face_up:
            return Source.FACE_UP
        if player.face_down:
            return Source.FACE_DOWN
        return None

    def _source_list(self, player: Player, source: Source) -> list[Card]:
        return getattr(player, source.value)

    # ---- legality --------------------------------------------------------

    def top_rank(self) -> int | None:
        return self.pile[-1].rank if self.pile else None

    def under_reverse_active(self) -> bool:
        return self.top_rank() == self.config.reverse_rank

    def is_legal_rank(self, rank: int) -> bool:
        if rank in (WILD_RESET, BURN_CARD):
            return True
        top = self.top_rank()
        if top is None:
            return True
        if self.under_reverse_active():
            reverse = self.config.reverse_rank
            if rank == reverse:
                return self.config.same_on_reverse
            return rank < reverse
        return rank >= top

    def is_legal_play(self, cards: list[Card]) -> bool:
        if not cards:
            return False
        if len({c.rank for c in cards}) != 1:
            return False
        return self.is_legal_rank(cards[0].rank)

    def has_legal_move(self, player: Player) -> bool:
        source = self.active_source(player)
        if source is None:
            return False
        if source is Source.FACE_DOWN:
            return True
        for card in self._source_list(player, source):
            if self.is_legal_rank(card.rank):
                return True
        return False

    # ---- actions ---------------------------------------------------------

    def play(self, pid: str, source: Source, indices: list[int]) -> PlayResult:
        if self.game_over:
            return PlayResult(ok=False, error="game is over")
        if self.phase != "playing":
            return PlayResult(ok=False, error="still setting up — pick your face-up cards")
        player = self.player(pid)
        if player is not self.current_player:
            return PlayResult(ok=False, error="not your turn")
        expected = self.active_source(player)
        if expected is None:
            return PlayResult(ok=False, error="you have no cards left")
        if source is not expected:
            return PlayResult(ok=False, error=f"must play from {expected.value}")
        cards_in = self._source_list(player, source)
        if not indices or len(set(indices)) != len(indices):
            return PlayResult(ok=False, error="invalid card selection")
        if any(i < 0 or i >= len(cards_in) for i in indices):
            return PlayResult(ok=False, error="card index out of range")

        chosen = [cards_in[i] for i in indices]

        if source is Source.FACE_DOWN:
            if len(indices) != 1:
                return PlayResult(ok=False, error="play one face-down card at a time")
            return self._play_face_down(player, indices[0], chosen[0])

        if not self.is_legal_play(chosen):
            return PlayResult(ok=False, error="illegal play")

        return self._commit_play(player, source, indices, chosen)

    def _play_face_down(self, player: Player, idx: int, card: Card) -> PlayResult:
        del player.face_down[idx]
        if self.is_legal_play([card]):
            return self._apply_committed_cards(player, [card], revealed=card)
        # Illegal blind reveal — pick up pile + the revealed card.
        player.hand.extend(self.pile)
        player.hand.append(card)
        self.pile = []
        self._record(
            f"{player.name} flipped {card.label} (illegal) and picked up",
            actor_pid=player.pid,
            picked_up=True,
        )
        # Pickup ends the picker's turn — see game-engine spec.
        self._advance_turn()
        return PlayResult(ok=True, picked_up=True, revealed=card)

    def _commit_play(
        self, player: Player, source: Source, indices: list[int], chosen: list[Card]
    ) -> PlayResult:
        cards_in = self._source_list(player, source)
        for i in sorted(indices, reverse=True):
            del cards_in[i]
        return self._apply_committed_cards(player, chosen)

    def _apply_committed_cards(
        self, player: Player, chosen: list[Card], revealed: Card | None = None
    ) -> PlayResult:
        self.pile.extend(chosen)
        rank = chosen[0].rank
        burned = False
        same_again = False

        if rank == BURN_CARD:
            self.pile = []
            burned = True
            same_again = True
        elif self._top_four_same():
            self.pile = []
            burned = True
            same_again = True

        self._refill_hand(player)

        finished_pid: str | None = None
        if not player.has_any_cards():
            player.finished = True
            finished_pid = player.pid
            self.finished_order.append(player.pid)
            same_again = False

        if revealed is not None:
            descr = f"flipped {revealed.label}"
        else:
            descr = f"played {', '.join(c.label for c in chosen)}"
        if burned:
            descr += " — burn!"
        self._record(
            f"{player.name} {descr}",
            actor_pid=player.pid,
            burned=burned,
            finished_pid=finished_pid,
        )

        game_over = self._check_game_over()
        if not game_over and not same_again:
            self._advance_turn()

        return PlayResult(
            ok=True,
            burned=burned,
            revealed=revealed,
            same_player_again=same_again and not game_over,
            finished_pid=finished_pid,
            game_over=game_over,
        )

    def end_round(self) -> PlayResult:
        """Host-driven early termination: rank remaining players by hand size
        and call the round done so the winner panel can render.
        """
        if self.game_over:
            return PlayResult(ok=False, error="game already over")
        remaining = [p for p in self.players if not p.finished]
        remaining.sort(
            key=lambda pl: (
                len(pl.hand) + len(pl.face_up) + len(pl.face_down),
                self.players.index(pl),
            )
        )
        for player in remaining:
            player.finished = True
            self.finished_order.append(player.pid)
        self.game_over = True
        self._record("round ended by host")
        return PlayResult(ok=True, game_over=True)

    def pickup(self, pid: str) -> PlayResult:
        if self.game_over:
            return PlayResult(ok=False, error="game is over")
        if self.phase != "playing":
            return PlayResult(ok=False, error="still setting up")
        player = self.player(pid)
        if player is not self.current_player:
            return PlayResult(ok=False, error="not your turn")
        if not self.pile:
            return PlayResult(ok=False, error="no pile to pick up")
        player.hand.extend(self.pile)
        self.pile = []
        self._record(
            f"{player.name} picked up the pile",
            actor_pid=player.pid,
            picked_up=True,
        )
        # Pickup ends the picker's turn — see game-engine spec.
        self._advance_turn()
        return PlayResult(ok=True, picked_up=True)

    # ---- helpers ---------------------------------------------------------

    def _record(
        self,
        text: str,
        *,
        actor_pid: str | None = None,
        burned: bool = False,
        picked_up: bool = False,
        finished_pid: str | None = None,
    ) -> None:
        """Append an event to last_actions, dropping the oldest when over cap."""
        self.last_actions.append(
            {
                "text": text,
                "actor_pid": actor_pid,
                "burned": burned,
                "picked_up": picked_up,
                "finished_pid": finished_pid,
            }
        )
        if len(self.last_actions) > LAST_ACTIONS_CAP:
            del self.last_actions[: len(self.last_actions) - LAST_ACTIONS_CAP]

    def _refill_hand(self, player: Player) -> None:
        while len(player.hand) < HAND_SIZE and self.deck:
            player.hand.append(self.deck.pop())

    def _top_four_same(self) -> bool:
        if len(self.pile) < 4:
            return False
        top4 = self.pile[-4:]
        return len({c.rank for c in top4}) == 1

    def _advance_turn(self) -> None:
        for _ in range(len(self.players)):
            self.current_idx = (self.current_idx + 1) % len(self.players)
            if not self.current_player.finished:
                return

    def _check_game_over(self) -> bool:
        remaining = [p for p in self.players if not p.finished]
        if len(remaining) <= 1:
            self.game_over = True
            if remaining:
                # The lone holdout finishes last.
                self.finished_order.append(remaining[0].pid)
        return self.game_over

    # ---- serialization ---------------------------------------------------

    def public_state(self, bot_pids: set[str] | None = None) -> dict:
        bot_set = bot_pids or set()
        return {
            "phase": self.phase,
            "config": self.config.to_dict(),
            "deck_count": len(self.deck),
            "pile_top": self.pile[-1].to_dict() if self.pile else None,
            "pile_size": len(self.pile),
            "current_pid": (
                self.current_player.pid if not self.game_over and self.phase == "playing" else None
            ),
            "under_reverse": self.under_reverse_active(),
            # Legacy alias retained for one release for old clients still
            # checking `view.under_seven` — same value as `under_reverse`.
            "under_seven": self.under_reverse_active(),
            "last_actions": [dict(entry) for entry in self.last_actions],
            # Legacy single-string alias — equals the newest entry's text, or "".
            "last_action": (self.last_actions[-1]["text"] if self.last_actions else ""),
            "game_over": self.game_over,
            "finished_order": list(self.finished_order),
            "players": [
                {
                    "pid": p.pid,
                    "name": p.name,
                    "hand_count": len(p.hand),
                    "face_up": [c.to_dict() for c in p.face_up],
                    "face_down_count": len(p.face_down),
                    "finished": p.finished,
                    "ready": p.ready,
                    "is_bot": p.pid in bot_set,
                }
                for p in self.players
            ],
        }

    def view_for(self, pid: str, bot_pids: set[str] | None = None) -> dict:
        state = self.public_state(bot_pids=bot_pids)
        me = self.player(pid)
        is_playing = self.phase == "playing"
        state["you"] = {
            "pid": me.pid,
            "hand": [c.to_dict() for c in me.hand],
            "choose": [c.to_dict() for c in me.choose],
            "ready": me.ready,
            "active_source": (
                self.active_source(me).value if is_playing and self.active_source(me) else None
            ),
            "your_turn": is_playing and not self.game_over and me is self.current_player,
            "can_play": (
                self.has_legal_move(me) if is_playing and me is self.current_player else False
            ),
        }
        return state
