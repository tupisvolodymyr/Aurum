"""Pure "Golden Wheel" logic: weighted multiplier segments, RNG.

No FastAPI/DB imports — unit- and statistically-testable in isolation,
same philosophy as app/games/slots.py.

The player picks ONE multiplier to bet on before spinning. If the wheel
lands on that multiplier, the payout is bet * multiplier; otherwise the
bet is lost. Segment weights are tuned so every individual multiplier
choice carries a broadly similar house edge — none of them should be a
mathematically "better" bet than the others (see tests/test_wheel.py).
"""

import secrets
from typing import NamedTuple


class WheelSegment(NamedTuple):
    multiplier: int
    weight: int  # relative arc size — bigger weight = bigger slice = more likely


# Ordered from most to least likely. Bigger multiplier -> smaller slice.
SEGMENTS: tuple[WheelSegment, ...] = (
    WheelSegment(multiplier=2, weight=45),
    WheelSegment(multiplier=3, weight=30),
    WheelSegment(multiplier=5, weight=18),
    WheelSegment(multiplier=10, weight=9),
    WheelSegment(multiplier=20, weight=4),
    WheelSegment(multiplier=40, weight=2),
)

TOTAL_WEIGHT = sum(segment.weight for segment in SEGMENTS)
MULTIPLIERS: tuple[int, ...] = tuple(segment.multiplier for segment in SEGMENTS)

# secrets.SystemRandom draws from the OS CSPRNG — same reasoning as slots.py.
_rng = secrets.SystemRandom()


def spin_wheel() -> int:
    """Returns the multiplier the wheel lands on."""
    roll = _rng.randrange(TOTAL_WEIGHT)
    cumulative = 0
    for segment in SEGMENTS:
        cumulative += segment.weight
        if roll < cumulative:
            return segment.multiplier
    return SEGMENTS[-1].multiplier  # unreachable; keeps type checkers happy
