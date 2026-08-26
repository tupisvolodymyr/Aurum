"""Pure slot-machine logic: RNG, reels, paytable.

Deliberately has no FastAPI/DB imports so it can be unit- and
statistically-tested in isolation from the web layer.
"""

import secrets
from enum import Enum
from typing import NamedTuple

REEL_COUNT = 3


class Symbol(str, Enum):
    CHERRY = "🍒"
    LEMON = "🍋"
    ORANGE = "🍊"
    BELL = "🔔"
    STAR = "⭐"
    DIAMOND = "💎"
    SEVEN = "7️⃣"


# Relative weight per reel stop, out of 100. Rarer symbols pay more —
# see PAYTABLE below and tests/test_slots.py for the resulting RTP (~90%).
REEL_WEIGHTS: dict[Symbol, int] = {
    Symbol.CHERRY: 30,
    Symbol.LEMON: 25,
    Symbol.ORANGE: 20,
    Symbol.BELL: 12,
    Symbol.STAR: 8,
    Symbol.DIAMOND: 4,
    Symbol.SEVEN: 1,
}

# Payout multiplier applied to the bet when all three reels match.
PAYTABLE: dict[Symbol, int] = {
    Symbol.CHERRY: 5,
    Symbol.LEMON: 8,
    Symbol.ORANGE: 10,
    Symbol.BELL: 25,
    Symbol.STAR: 50,
    Symbol.DIAMOND: 150,
    Symbol.SEVEN: 500,
}

# Any two matching symbols (regardless of which one) refunds the bet —
# a "near miss" push, common in real slots to soften variance.
TWO_OF_A_KIND_MULTIPLIER = 1

_WEIGHTED_POOL: list[Symbol] = [symbol for symbol, weight in REEL_WEIGHTS.items() for _ in range(weight)]

# secrets.SystemRandom draws from the OS CSPRNG (unlike random's default
# Mersenne Twister, which is predictable if enough output is observed) —
# the right choice for anything gambling-adjacent, even with play money.
_rng = secrets.SystemRandom()


class SpinResult(NamedTuple):
    reels: tuple[Symbol, ...]
    multiplier: int


def spin_reels() -> tuple[Symbol, ...]:
    return tuple(_rng.choice(_WEIGHTED_POOL) for _ in range(REEL_COUNT))


def evaluate(reels: tuple[Symbol, ...]) -> int:
    """Payout multiplier for a given reel outcome (0 = no win)."""
    counts: dict[Symbol, int] = {}
    for symbol in reels:
        counts[symbol] = counts.get(symbol, 0) + 1

    best_count = max(counts.values())
    if best_count == REEL_COUNT:
        symbol = next(s for s, c in counts.items() if c == REEL_COUNT)
        return PAYTABLE[symbol]
    if best_count == 2:
        return TWO_OF_A_KIND_MULTIPLIER
    return 0


def play() -> SpinResult:
    reels = spin_reels()
    return SpinResult(reels=reels, multiplier=evaluate(reels))
