"""
Render an OG social-card PNG (1200x630) summarizing the key numbers of a
TradeReport. Matches basiscalc.xyz dark theme (emerald accent).
"""
from decimal import Decimal
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

from paper_vs_real.types import TradeReport

BG = "#0a0e17"
CARD = "#121826"
EMERALD = "#16a34a"
RED = "#dc2626"
TEXT = "#f5f6fa"
MUTED = "#9ca3af"


def render_og_image(report: TradeReport, target_handle: str, out_path: Path) -> None:
    fig = plt.figure(figsize=(12, 6.3), dpi=100, facecolor=BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 100); ax.set_ylim(0, 100)
    ax.axis("off")
    ax.set_facecolor(BG)

    # Header
    ax.text(5, 90, "Paper PnL vs Real  —  Episode 1",
            color=MUTED, fontsize=16, weight="bold")
    ax.text(5, 82, f"{target_handle} on Hyperliquid",
            color=TEXT, fontsize=22, weight="bold")

    # Card
    rect = FancyBboxPatch((5, 22), 90, 50, boxstyle="round,pad=0,rounding_size=2",
                          linewidth=0, facecolor=CARD)
    ax.add_patch(rect)

    def fmt(d: Decimal) -> str:
        q = d.quantize(Decimal("1"))
        sign = "-" if q < 0 else ""
        return f"{sign}${abs(q):,.0f}"

    paper = report.paper_pnl
    realized = report.realized_pnl_from_chain
    friction = report.costs.fees + report.costs.funding
    net = realized - friction

    cols = [
        ("He said",       fmt(paper),    EMERALD),
        ("Chain says",    fmt(realized), MUTED),
        ("After friction", fmt(net),     RED),
    ]
    xs = [20, 50, 80]
    for x, (label, val, color) in zip(xs, cols):
        ax.text(x, 58, label, color=MUTED, fontsize=16, ha="center")
        ax.text(x, 40, val, color=color, fontsize=34, ha="center", weight="bold")

    # Footer
    ax.text(50, 10, "basiscalc.xyz", color=EMERALD, fontsize=18, ha="center", weight="bold")

    fig.savefig(out_path, facecolor=BG, bbox_inches=None, pad_inches=0, dpi=100)
    plt.close(fig)


if __name__ == "__main__":
    import json, sys, os
    from decimal import Decimal
    from datetime import datetime
    from paper_vs_real.types import TradeWindow, CostBreakdown, TradeReport

    payload = json.loads(Path(sys.argv[1]).read_text())
    window = TradeWindow(
        wallet=payload["wallet"], asset=payload["asset"],
        start=datetime.fromisoformat(payload["window"]["start"]),
        end=datetime.fromisoformat(payload["window"]["end"]),
    )
    costs = CostBreakdown(
        fees=Decimal(payload["costs"]["fees"]),
        funding=Decimal(payload["costs"]["funding"]),
        slippage_mid=Decimal(payload["costs"]["slippage"]["mid"]),
        slippage_low=Decimal(payload["costs"]["slippage"]["low"]),
        slippage_high=Decimal(payload["costs"]["slippage"]["high"]),
    )
    paper = Decimal(payload["paper_pnl"])
    report = TradeReport(
        window=window, entry_fills=(), exit_fills=(), funding_events=(),
        costs=costs,
        paper_pnl=paper,
        real_pnl_mid=Decimal(payload["real_pnl"]["mid"]),
        real_pnl_low=Decimal(payload["real_pnl"]["low"]),
        real_pnl_high=Decimal(payload["real_pnl"]["high"]),
        realized_pnl_from_chain=Decimal(payload.get("realized_pnl_from_chain", "0")),
    )
    target = os.environ.get("TARGET_HANDLE", "@target")
    render_og_image(report, target, Path(sys.argv[2]))
    print(f"wrote {sys.argv[2]}")
