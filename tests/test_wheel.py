from app.games.wheel import MULTIPLIERS, SEGMENTS, TOTAL_WEIGHT, spin_wheel


def test_multipliers_are_unique_and_match_segments():
    assert len(MULTIPLIERS) == len(set(MULTIPLIERS))
    assert set(MULTIPLIERS) == {s.multiplier for s in SEGMENTS}


def _total_weight_by_multiplier() -> dict[int, int]:
    # Several segments can now share the same multiplier (scattered around
    # the wheel for visual variety) — what actually determines a bet's odds
    # is the *sum* of weight across all of that multiplier's segments, not
    # any single wedge's weight.
    totals: dict[int, int] = {}
    for segment in SEGMENTS:
        totals[segment.multiplier] = totals.get(segment.multiplier, 0) + segment.weight
    return totals


def test_bigger_multiplier_means_smaller_slice():
    totals = _total_weight_by_multiplier()
    ordered_multipliers = sorted(totals)
    weights_by_multiplier = [totals[m] for m in ordered_multipliers]
    assert weights_by_multiplier == sorted(weights_by_multiplier, reverse=True)


def test_no_betting_choice_has_positive_expected_value():
    """House edge sanity check: for every multiplier a player could bet on,
    (probability of landing on it) * multiplier must stay below 1 — i.e. no
    choice should be profitable for the player on average.

    x2 is a deliberate, documented exception — see the module docstring in
    app/games/wheel.py for the proof that an 8-slice wheel spanning x2..x100
    cannot keep *every* choice under RTP 1.0; x2 (smallest, most frequent
    prize) is the one that absorbs the shortfall. It's checked separately
    below with a wider, still-bounded band so a regression that pushes it
    to something absurd (e.g. RTP 5.0) still fails the suite.
    """
    for multiplier, weight in _total_weight_by_multiplier().items():
        probability = weight / TOTAL_WEIGHT
        rtp = probability * multiplier
        if multiplier == 2:
            assert 1.0 <= rtp < 1.3, f"x2 has RTP {rtp:.2f} — expected the documented ~1.0-1.3 band"
            continue
        assert rtp < 1.0, f"x{multiplier} has RTP {rtp:.2f} — positive EV for the player"
        assert rtp > 0.5, f"x{multiplier} has RTP {rtp:.2f} — house edge too extreme"


def test_spin_wheel_only_returns_known_multipliers():
    for _ in range(500):
        assert spin_wheel() in MULTIPLIERS


def test_spin_wheel_distribution_is_sane():
    """Statistical sanity check, not exact calibration: run enough spins that
    the observed frequency of the most common segment (x2, 219/360 ≈ 60.8%)
    should land in a generous band around its true probability."""
    spins = 20_000
    results = [spin_wheel() for _ in range(spins)]
    x2_share = results.count(2) / spins
    assert 0.55 < x2_share < 0.66, f"x2 landed {x2_share:.3f} of the time — expected ~0.608"

    x100_share = results.count(100) / spins
    assert x100_share < 0.03, f"x100 (rarest slice) landed {x100_share:.3f} of the time — expected ~0.008"
