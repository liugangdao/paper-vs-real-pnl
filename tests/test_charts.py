import dataclasses
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timedelta, timezone

from paper_vs_real.charts import render_waterfall, render_funding_cumulative
from paper_vs_real.types import (
    CostBreakdown, FundingEvent, TradeWindow, TradeReport,
)


def _sample_report() -> TradeReport:
    window = TradeWindow(
        wallet="0xabc", asset="BTC",
        start=datetime(2026, 3, 1, tzinfo=timezone.utc),
        end=datetime(2026, 3, 5, tzinfo=timezone.utc),
    )
    events = tuple(
        FundingEvent(
            timestamp=window.start + timedelta(hours=h),
            amount=Decimal("-50"),
        )
        for h in range(0, 96, 8)
    )
    costs = CostBreakdown(
        fees=Decimal("150"),
        funding=Decimal("600"),
        slippage_mid=Decimal("2500"),
        slippage_low=Decimal("2000"),
        slippage_high=Decimal("3000"),
    )
    paper = Decimal("100000")
    return TradeReport(
        window=window,
        entry_fills=(), exit_fills=(), funding_events=events,
        costs=costs,
        paper_pnl=paper,
        real_pnl_mid=paper - costs.total_mid,
        real_pnl_low=paper - costs.total_high,
        real_pnl_high=paper - costs.total_low,
    )


def test_render_waterfall_writes_png(tmp_path):
    out = tmp_path / "waterfall.png"
    render_waterfall(_sample_report(), out)
    assert out.exists()
    assert out.stat().st_size > 1000


def test_render_funding_cumulative_writes_png(tmp_path):
    out = tmp_path / "funding.png"
    render_funding_cumulative(_sample_report(), out)
    assert out.exists()
    assert out.stat().st_size > 1000


def test_render_waterfall_shows_realized_when_meaningfully_different(tmp_path):
    report = _sample_report()
    report3 = TradeReport(
        window=report.window,
        entry_fills=(),
        exit_fills=(),
        funding_events=report.funding_events,
        costs=report.costs,
        paper_pnl=Decimal("30000000"),
        real_pnl_mid=Decimal("28600000"),
        real_pnl_low=Decimal("28000000"),
        real_pnl_high=Decimal("29000000"),
        realized_pnl_from_chain=Decimal("20000000"),
    )
    out = tmp_path / "wf.png"
    render_waterfall(report3, out)
    assert out.exists() and out.stat().st_size > 1000


def test_render_waterfall_skips_slippage_when_zero(tmp_path):
    report = _sample_report()
    costs_no_slip = CostBreakdown(
        fees=report.costs.fees,
        funding=report.costs.funding,
        slippage_mid=Decimal("0"),
        slippage_low=Decimal("0"),
        slippage_high=Decimal("0"),
    )
    report2 = TradeReport(
        window=report.window,
        entry_fills=(),
        exit_fills=(),
        funding_events=report.funding_events,
        costs=costs_no_slip,
        paper_pnl=report.paper_pnl,
        real_pnl_mid=report.paper_pnl - costs_no_slip.total_mid,
        real_pnl_low=report.paper_pnl - costs_no_slip.total_high,
        real_pnl_high=report.paper_pnl - costs_no_slip.total_low,
    )
    out = tmp_path / "wf_no_slip.png"
    render_waterfall(report2, out)
    assert out.exists() and out.stat().st_size > 1000


def test_render_funding_cumulative_with_no_events(tmp_path):
    # Edge: trader's funding events list is empty
    report = _sample_report()
    report = TradeReport(
        window=report.window,
        entry_fills=report.entry_fills,
        exit_fills=report.exit_fills,
        funding_events=(),
        costs=report.costs,
        paper_pnl=report.paper_pnl,
        real_pnl_mid=report.real_pnl_mid,
        real_pnl_low=report.real_pnl_low,
        real_pnl_high=report.real_pnl_high,
    )
    out = tmp_path / "funding.png"
    render_funding_cumulative(report, out)
    assert out.exists()
