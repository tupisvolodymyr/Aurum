from app.games.slots import PAYTABLE, Symbol, evaluate, play


def test_three_of_a_kind_pays_paytable_multiplier():
    for symbol, multiplier in PAYTABLE.items():
        assert evaluate((symbol, symbol, symbol)) == multiplier


def test_two_of_a_kind_pays_flat_refund():
    assert evaluate((Symbol.CHERRY, Symbol.CHERRY, Symbol.LEMON)) == 1
    assert evaluate((Symbol.SEVEN, Symbol.DIAMOND, Symbol.SEVEN)) == 1


def test_no_match_pays_nothing():
    assert evaluate((Symbol.CHERRY, Symbol.LEMON, Symbol.ORANGE)) == 0


def test_rtp_is_in_a_sane_range():
    """Statistical sanity check, not an exact calibration: a paytable or
    weight typo that meaningfully breaks the house edge should fail this;
    ordinary sampling noise should not.
    """
    spins = 40_000
    total_return = sum(play().multiplier for _ in range(spins))
    rtp = total_return / spins  # bet of 1 per spin, so total_bet == spins

    assert 0.80 < rtp < 1.00, f"RTP {rtp:.3f} outside expected ~90% range — check PAYTABLE/REEL_WEIGHTS"
