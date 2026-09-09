"""Pure "Golden Wheel" logic: weighted multiplier segments, RNG.

No FastAPI/DB imports — unit- and statistically-testable in isolation,
same philosophy as app/games/slots.py.

The player picks ONE multiplier to bet on before spinning. If the wheel
lands on any segment carrying that multiplier, the payout is bet *
multiplier; otherwise the bet is lost.

Eight segments, matching the reference casino-wheel design exactly (same
clockwise order from the top): x100, x50, x20, x10, x5, x5, x2, x25.
app/static/js/wheel.js's SEGMENTS must mirror this — same order, same
angle boundaries derived from these weights (TOTAL_WEIGHT is deliberately
360 so a weight can be read directly as a degree width).

A mathematical note on fairness: with only 8 slices and a payout spread
from x2 to x100, it is *impossible* for every choice to carry RTP < 1.
Proof sketch: the largest slice that keeps multiplier m's RTP under 1 is
360/m degrees; summing 360/m across {2, 5(x2), 10, 20, 25, 50, 100} caps
out at ~331° — 29° short of the 360° the wheel actually has to cover, even
before x2 (the most common, lowest-stakes prize) claims any slice at all.
The remaining ~29° has to land somewhere, and every other multiplier is
already sitting at its own RTP-safe ceiling — so x2 absorbs it. Every
*other* choice here is comfortably under 1.0 (0.83–0.94); only x2 sits
slightly over (~1.22), i.e. mildly in the player's favor on the smallest,
most frequent prize. See test_wheel.py for the exact assertions.
"""

import secrets
from typing import NamedTuple


class WheelSegment(NamedTuple):
    multiplier: int
    weight: int  # degrees of arc (TOTAL_WEIGHT == 360) — bigger = more likely


# Clockwise from the top (12 o'clock), matching the reference wheel exactly.
SEGMENTS: tuple[WheelSegment, ...] = (
    WheelSegment(multiplier=100, weight=3),
    WheelSegment(multiplier=50, weight=6),
    WheelSegment(multiplier=20, weight=17),
    WheelSegment(multiplier=10, weight=34),
    WheelSegment(multiplier=5, weight=34),
    WheelSegment(multiplier=5, weight=34),
    WheelSegment(multiplier=2, weight=219),
    WheelSegment(multiplier=25, weight=13),
)

TOTAL_WEIGHT = sum(segment.weight for segment in SEGMENTS)
assert TOTAL_WEIGHT == 360, "SEGMENTS must cover exactly 360 degrees"

# Deduped, ascending — these are the seven *bettable* choices shown as
# picker buttons (x5 appears twice above but is one betting choice).
MULTIPLIERS: tuple[int, ...] = tuple(sorted({segment.multiplier for segment in SEGMENTS}))

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
