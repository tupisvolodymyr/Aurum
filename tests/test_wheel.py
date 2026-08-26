from app.games.wheel import MULTIPLIERS, SEGMENTS, TOTAL_WEIGHT, spin_wheel


def test_multipliers_are_unique_and_match_segments():
    assert len(MULTIPLIERS) == len(set(MULTIPLIERS))
    assert set(MULTIPLIERS) == {s.multiplier for s in SEGMENTS}


def test_bigger_multiplier_means_smaller_slice():
    # Segments are already ordered biggest-weight-first in the module; just
    # confirm that ordering actually holds as multiplier size increases.
    weights_by_multiplier = [s.weight for s in SEGMENTS]
    assert weights_by_multiplier == sorted(weights_by_multiplier, reverse=True)


def test_no_betting_choice_has_positive_expected_value():
    """House edge sanity check: for every multiplier a player could bet on,
    (probability of landing on it) * multiplier must stay below 1 — i.e. no
    choice should be profitable for the player on average."""
    for segment in SEGMENTS:
        probability = segment.weight / TOTAL_WEIGHT
        rtp = probability * segment.multiplier
        assert rtp < 1.0, f"x{segment.multiplier} has RTP {rtp:.2f} — positive EV for the player"
        assert rtp > 0.5, f"x{segment.multiplier} has RTP {rtp:.2f} — house edge too extreme"


def test_spin_wheel_only_returns_known_multipliers():
    for _ in range(500):
        assert spin_wheel() in MULTIPLIERS


def test_spin_wheel_distribution_is_sane():
    """Statistical sanity check, not exact calibration: run enough spins that
    the observed frequency of the most common segment (x2, 45/108 ≈ 41.7%)
    should land in a generous band around its true probability."""
    spins = 20_000
    results = [spin_wheel() for _ in range(spins)]
    x2_share = results.count(2) / spins
    assert 0.35 < x2_share < 0.48, f"x2 landed {x2_share:.3f} of the time — expected ~0.417"

    x40_share = results.count(40) / spins
    assert x40_share < 0.05, f"x40 (rarest slice) landed {x40_share:.3f} of the time — expected ~0.019"
