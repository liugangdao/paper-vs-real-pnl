import json
from decimal import Decimal
from datetime import datetime, timezone

from paper_vs_real.types import (
    Fill, FundingEvent, TradeWindow, CostBreakdown, TradeReport,
)
from paper_vs_real.report import to_json, to_markdown


def _sample_report() -> TradeReport:
    window = TradeWindow(
        wallet="0xabc",
        asset="BTC",
        start=datetime(2026, 3, 1, tzinfo=timezone.utc),
        end=datetime(2026, 3, 5, tzinfo=timezone.utc),
    )
    entry = Fill(
        timestamp=datetime(2026, 3, 1, tzinfo=timezone.utc),
        price=Decimal("65000"), size=Decimal("100"), side="buy",
        is_maker=False, fee_paid=Decimal("1.3"),
    )
    exit_ = Fill(
        timestamp=datetime(2026, 3, 5, tzinfo=timezone.utc),
        price=Decimal("68000"), size=Decimal("100"), side="sell",
        is_maker=True, fee_paid=Decimal("-0.34"),
    )
    funding = FundingEvent(timestamp=datetime(2026, 3, 2, tzinfo=timezone.utc), amount=Decimal("-112.5"))
    costs = CostBreakdown(
        fees=Decimal("0.96"),
        funding=Decimal("112.5"),
        slippage_mid=Decimal("2500"),
        slippage_low=Decimal("2000"),
        slippage_high=Decimal("3000"),
    )
    paper_pnl = Decimal("300000")
    return TradeReport(
        window=window,
        entry_fills=(entry,),
        exit_fills=(exit_,),
        funding_events=(funding,),
        costs=costs,
        paper_pnl=paper_pnl,
        real_pnl_mid=paper_pnl - costs.total_mid,
        real_pnl_low=paper_pnl - costs.total_high,
        real_pnl_high=paper_pnl - costs.total_low,
    )


def test_to_json_roundtrips_decimals_as_strings():
    report = _sample_report()
    payload = to_json(report)
    obj = json.loads(payload)
    assert obj["wallet"] == "0xabc"
    assert obj["asset"] == "BTC"
    assert obj["paper_pnl"] == "300000"
    assert obj["costs"]["fees"] == "0.96"
    assert obj["costs"]["funding"] == "112.5"
    assert obj["costs"]["slippage"]["mid"] == "2500"
    assert obj["real_pnl"]["mid"] == str(report.real_pnl_mid)


def test_to_markdown_renders_table_with_signed_values():
    md = to_markdown(_sample_report())
    assert "| Component" in md
    assert "Fees" in md
    assert "Funding" in md
    assert "Slippage" in md
    assert "300,000" in md or "300000" in md
    assert "Real PnL" in md
