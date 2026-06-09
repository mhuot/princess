#!/usr/bin/env python3
"""
Card primitives for Princess Card Game.

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

from dataclasses import dataclass

SUITS = ("S", "H", "D", "C")
RANKS = (2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14)

_RANK_LABEL = {11: "J", 12: "Q", 13: "K", 14: "A"}


@dataclass(frozen=True)
class Card:
    rank: int
    suit: str

    @property
    def label(self) -> str:
        return f"{_RANK_LABEL.get(self.rank, str(self.rank))}{self.suit}"

    def to_dict(self) -> dict:
        return {"rank": self.rank, "suit": self.suit, "label": self.label}

    @classmethod
    def from_dict(cls, data: dict) -> "Card":
        """Reconstruct a Card from a ``to_dict`` payload.

        ``label`` (when present) is recomputed from rank, so it is ignored on
        input. Missing ``rank``/``suit`` raises ``KeyError``.
        """
        return cls(rank=int(data["rank"]), suit=str(data["suit"]))


def make_deck() -> list[Card]:
    return [Card(r, s) for r in RANKS for s in SUITS]
