from decimal import Decimal
from datetime import datetime, timezone

from paper_vs_real.types import Fill
from paper_vs_real.compute import compute_fees


def _fill(fee: str, is_maker: bool = False) -> Fill:
    return Fill(
        timestamp=datetime(2026, 3, 1, tzinfo=timezone.utc),
        price=Decimal("65000"),
        size=Decimal("100"),
        side="buy",
        is_maker=is_maker,
        fee_paid=Decimal(fee),
    )


def test_all_taker_fills_sum_positive():
    fills = [_fill("10.0"), _fill("12.5")]
    assert compute_fees(fills) == Decimal("22.5")


def test_maker_rebate_reduces_net_fee():
    fills = [_fill("10.0", is_maker=False), _fill("-3.0", is_maker=True)]
    assert compute_fees(fills) == Decimal("7.0")


def test_all_maker_rebate_returns_negative():
    fills = [_fill("-2.0", is_maker=True), _fill("-1.5", is_maker=True)]
    assert compute_fees(fills) == Decimal("-3.5")


def test_empty_returns_zero():
    assert compute_fees([]) == Decimal("0")
