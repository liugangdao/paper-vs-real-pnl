from decimal import Decimal
from datetime import datetime, timezone

from paper_vs_real.types import Fill, FundingEvent, TradeWindow, CostBreakdown, TradeReport


def test_fill_signed_size_for_long_open():
    f = Fill(
        timestamp=datetime(2026, 3, 1, tzinfo=timezone.utc),
        price=Decimal("65000"),
        size=Decimal("100"),
        side="buy",
        is_maker=False,
        fee_paid=Decimal("1.3"),
    )
    assert f.signed_size == Decimal("100")


def test_fill_signed_size_for_short_open():
    f = Fill(
        timestamp=datetime(2026, 3, 1, tzinfo=timezone.utc),
        price=Decimal("65000"),
        size=Decimal("100"),
        side="sell",
        is_maker=True,
        fee_paid=Decimal("-0.3"),
    )
    assert f.signed_size == Decimal("-100")


def test_cost_breakdown_total():
    cb = CostBreakdown(
        fees=Decimal("150"),
        funding=Decimal("8000"),
        slippage_mid=Decimal("2500"),
        slippage_low=Decimal("2000"),
        slippage_high=Decimal("3000"),
    )
    assert cb.total_mid == Decimal("10650")
    assert cb.total_low == Decimal("10150")
    assert cb.total_high == Decimal("11150")
