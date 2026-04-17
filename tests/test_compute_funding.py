from decimal import Decimal
from datetime import datetime, timezone

from paper_vs_real.types import FundingEvent
from paper_vs_real.compute import compute_funding_cost


def _ev(amount: str) -> FundingEvent:
    return FundingEvent(timestamp=datetime(2026, 3, 1, tzinfo=timezone.utc), amount=Decimal(amount))


def test_all_paid_funding_is_positive_cost():
    # Hyperliquid reports funding paid as negative (money out); cost (positive) = -sum.
    events = [_ev("-50.0"), _ev("-62.5")]
    assert compute_funding_cost(events) == Decimal("112.5")


def test_received_funding_is_negative_cost():
    events = [_ev("100.0"), _ev("25.0")]
    assert compute_funding_cost(events) == Decimal("-125.0")


def test_mixed_sign_sums_correctly():
    events = [_ev("-50.0"), _ev("10.0"), _ev("-20.0")]
    assert compute_funding_cost(events) == Decimal("60.0")


def test_empty_returns_zero():
    assert compute_funding_cost([]) == Decimal("0")
