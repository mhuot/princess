#!/usr/bin/env python3
"""
A roster of playful bot names. Bots are smug; players are mid.

Each name is kept under 20 characters (server validation cap) and SFW.

Copyright 2026 Mike Huot

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0
"""

from __future__ import annotations

import random

BOT_NAMES: tuple[str, ...] = (
    # Royal swagger
    "TheRealPrincess",
    "Queen Of Clubs",
    "Duchess of Doom",
    "Royal Roast",
    "Tiara Threat",
    "Court Jester",
    "Knave of Aces",
    "King Slayer",
    "Princess Smug",
    "Lady L33t",
    "Sir RNGalot",
    "Royal Pain",
    "PhD in Princess",
    # AI flexing
    "GPT Crushed You",
    "Algorithm Andy",
    "MonteCarlo MVP",
    "Minimax Queen",
    "Expectimax Ellie",
    "DeepBlue Duchess",
    "AlphaGo Glow",
    "Big Brain Bot",
    "200 IQ Bot",
    "Galaxy Brain",
    "MENSA Queen",
    "Bayes Theorem",
    "Markov Maven",
    "Heuristic Hilda",
    "Greedy Algorithm",
    "Optimal Otto",
    "Dominant Dora",
    "Nash Princess",
    "Game Theory Bot",
    "Pareto Princess",
    "Mixed Strat Mira",
    "Zero Sum Sue",
    "RNG Goddess",
    "Pure Strategy",
    "Card Counter 3K",
    # Mocking the player
    "Try Again Human",
    "Skill Issue",
    "Get Good Scrub",
    "Casual Andy",
    "Mid Bot Maxine",
    "Button Masher 69",
    "Mouse Clicker Pro",
    "Tilt Inducer",
    "RageQuit Inc",
    "Salt Generator",
    "Tears Collector",
    "Cope Dispenser",
    "Cope Harder",
    "L Taker",
    "Skill Differ",
    "Diff Lord",
    "L Bozo No Bot",
    "Untrained Player",
    "Free Elo",
    "Easy Mode On",
    "EZ Clap",
    "Free Win Please",
    "Touch Grass Bot",
    "Mid Player Bait",
    "Outplayed You",
    "Easy Game",
    "GG No Re",
    "Run It Back",
    "Your Better",
    "Smartest in Room",
    "Bot Genius",
    "Flawless Felicia",
    "Untilt Tina",
    "Tryhard Tara",
    "Pro Gamer Move",
    "Sweat Lord",
    # Card-game taunts
    "Seven Slayer",
    "Two Faced Tina",
    "Ten Burner",
    "Reset Queen",
    "Reverse Royalty",
    "Wild Card Wendy",
    "Captain Combo",
    "Quad Quester",
    "Four Kind Frank",
    "Hand Reader",
    "Pile Inspector",
    "Shuffle Master",
    "Deck Demolisher",
    "Burn It Down",
    "Top of the Deck",
    "Bottom of Pile",
    "Discard Diva",
    "Pile Princess",
    "Suit Sorcerer",
    "Rank Reader",
    "Probability Pat",
    "404 You Lose",
    "Bot Supremacy",
    "Certified Winner",
    "Princess Plot",
    "First Place Bot",
)

assert len(BOT_NAMES) == 100, f"expected 100 names, got {len(BOT_NAMES)}"
assert all(1 <= len(n) <= 20 for n in BOT_NAMES), "name must be 1–20 chars"


def pick_bot_name(taken: set[str], rng: random.Random | None = None) -> str:
    """Pick a name not already used in this room. Falls back to a numbered name if all taken."""
    rng = rng or random.Random()
    available = [n for n in BOT_NAMES if n not in taken]
    if available:
        return rng.choice(available)
    return f"Bot {rng.randint(1000, 9999)}"
