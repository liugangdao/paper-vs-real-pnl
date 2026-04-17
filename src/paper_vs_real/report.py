import json
from decimal import Decimal

from paper_vs_real.types import TradeReport


def _fmt_usd(d: Decimal) -> str:
    quant = d.quantize(Decimal("0.01"))
    sign = "-" if quant < 0 else ""
    magnitude = abs(quant)
    return f"{sign}${magnitude:,.2f}"


def to_json(report: TradeReport) -> str:
    obj = {
        "wallet": report.window.wallet,
        "asset": report.window.asset,
        "window": {
            "start": report.window.start.isoformat(),
            "end": report.window.end.isoformat(),
        },
        "n_entry_fills": len(report.entry_fills),
        "n_exit_fills": len(report.exit_fills),
        "n_funding_events": len(report.funding_events),
        "paper_pnl": str(report.paper_pnl),
        "realized_pnl_from_chain": str(report.realized_pnl_from_chain),
        "costs": {
            "fees": str(report.costs.fees),
            "funding": str(report.costs.funding),
            "slippage": {
                "mid": str(report.costs.slippage_mid),
                "low": str(report.costs.slippage_low),
                "high": str(report.costs.slippage_high),
            },
            "total": {
                "mid": str(report.costs.total_mid),
                "low": str(report.costs.total_low),
                "high": str(report.costs.total_high),
            },
        },
        "real_pnl": {
            "mid": str(report.real_pnl_mid),
            "low": str(report.real_pnl_low),
            "high": str(report.real_pnl_high),
        },
    }
    return json.dumps(obj, indent=2)


def to_markdown(report: TradeReport) -> str:
    c = report.costs
    rows = [
        "| Component | Amount |",
        "|-----------|--------|",
        f"| Paper PnL | {_fmt_usd(report.paper_pnl)} |",
        f"| Realized PnL (chain records) | {_fmt_usd(report.realized_pnl_from_chain)} |",
        f"| Fees (signed) | {_fmt_usd(c.fees)} |",
        f"| Funding cost | {_fmt_usd(c.funding)} |",
        f"| Slippage (mid) | {_fmt_usd(c.slippage_mid)} |",
        f"| Slippage (low–high) | {_fmt_usd(c.slippage_low)} – {_fmt_usd(c.slippage_high)} |",
        f"| **Real PnL (mid)** | **{_fmt_usd(report.real_pnl_mid)}** |",
        f"| Real PnL (low–high) | {_fmt_usd(report.real_pnl_low)} – {_fmt_usd(report.real_pnl_high)} |",
    ]
    return "\n".join(rows)
