import argparse
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from paper_vs_real.fetch import (
    HyperliquidClient, fetch_fills_sequential, fetch_funding, fetch_candles,
)
from paper_vs_real.compute import (
    compute_fees, compute_funding_cost, compute_slippage,
)
from paper_vs_real.types import (
    TradeWindow, CostBreakdown, TradeReport,
)
from paper_vs_real.report import to_json, to_markdown


def _parse_iso(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def run(
    *,
    wallet: str,
    asset: str,
    start_iso: str,
    end_iso: str,
    paper_pnl: str,
    out_dir: Path,
    client: HyperliquidClient | None = None,
) -> TradeReport:
    client = client or HyperliquidClient()
    window = TradeWindow(
        wallet=wallet, asset=asset,
        start=_parse_iso(start_iso), end=_parse_iso(end_iso),
    )

    entry, exit_ = fetch_fills_sequential(
        client,
        wallet=wallet,
        start=window.start,
        end=window.end,
        asset=asset,
        split_entry_exit=True,
    )
    funding = fetch_funding(client, wallet=wallet, start=window.start, end=window.end)
    candles = fetch_candles(client, asset=asset, start=window.start, end=window.end, interval="1m")

    all_fills = list(entry) + list(exit_)
    fees = compute_fees(all_fills)
    funding_cost = compute_funding_cost(funding)
    slip = compute_slippage(all_fills, candles)
    realized_pnl = sum((f.closed_pnl for f in all_fills), start=Decimal("0"))

    costs = CostBreakdown(
        fees=fees,
        funding=funding_cost,
        slippage_mid=slip.mid,
        slippage_low=slip.low,
        slippage_high=slip.high,
    )
    paper = Decimal(paper_pnl)
    report = TradeReport(
        window=window,
        entry_fills=tuple(entry),
        exit_fills=tuple(exit_),
        funding_events=tuple(funding),
        costs=costs,
        paper_pnl=paper,
        real_pnl_mid=paper - costs.total_mid,
        real_pnl_low=paper - costs.total_high,
        real_pnl_high=paper - costs.total_low,
        realized_pnl_from_chain=realized_pnl,
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.json").write_text(to_json(report))
    (out_dir / "report.md").write_text(to_markdown(report))

    from paper_vs_real.charts import render_waterfall, render_funding_cumulative
    render_waterfall(report, out_dir / "waterfall.png")
    render_funding_cumulative(report, out_dir / "funding.png")

    return report


def main() -> None:
    p = argparse.ArgumentParser(prog="paper-vs-real")
    p.add_argument("--wallet", required=True)
    p.add_argument("--asset", required=True, help="e.g., BTC")
    p.add_argument("--from", dest="start_iso", required=True, help="ISO 8601 start")
    p.add_argument("--to", dest="end_iso", required=True, help="ISO 8601 end")
    p.add_argument("--paper-pnl", required=True, help="target-claimed profit in USD, e.g. 300000")
    p.add_argument("--out", default="outputs", help="output directory")
    args = p.parse_args()

    run(
        wallet=args.wallet,
        asset=args.asset,
        start_iso=args.start_iso,
        end_iso=args.end_iso,
        paper_pnl=args.paper_pnl,
        out_dir=Path(args.out),
    )
