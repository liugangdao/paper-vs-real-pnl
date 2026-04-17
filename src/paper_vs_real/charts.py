from decimal import Decimal
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from paper_vs_real.types import TradeReport

EMERALD = "#16a34a"
RED = "#dc2626"
GRAY = "#64748b"
TEXT = "#1a2332"


def render_waterfall(report: TradeReport, out_path: Path) -> None:
    """
    Bars left to right: Paper PnL, minus Fees, minus Funding, minus Slippage (with error bar), equals Real PnL.
    """
    c = report.costs
    labels = ["Paper PnL", "Fees", "Funding", "Slippage", "Real PnL"]
    values = [
        float(report.paper_pnl),
        -float(c.fees),
        -float(c.funding),
        -float(c.slippage_mid),
        float(report.real_pnl_mid),
    ]
    cumulative = [values[0]]
    for v in values[1:-1]:
        cumulative.append(cumulative[-1] + v)
    cumulative.append(values[-1])

    fig, ax = plt.subplots(figsize=(10, 5), dpi=150)
    x = range(len(labels))

    for i, (label, val, cum) in enumerate(zip(labels, values, cumulative)):
        if i == 0 or i == len(labels) - 1:
            ax.bar(i, val, color=EMERALD if i == 0 else GRAY, edgecolor=TEXT)
        else:
            bottom = cumulative[i - 1] + val
            ax.bar(i, -val, bottom=bottom, color=RED, edgecolor=TEXT)

    # Slippage error band (index 3)
    slip_lo = float(c.slippage_low)
    slip_hi = float(c.slippage_high)
    slip_mid = float(c.slippage_mid)
    cum_after_funding = cumulative[2]
    ax.errorbar(
        3,
        cum_after_funding - slip_mid,
        yerr=[[slip_mid - slip_lo], [slip_hi - slip_mid]],
        fmt="none", color=TEXT, capsize=6, linewidth=1.5,
    )

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=11)
    ax.set_ylabel("USD", fontsize=11)
    ax.set_title("Paper PnL vs Real PnL — cost waterfall", fontsize=13, color=TEXT)
    ax.yaxis.set_major_formatter(lambda v, _: f"${v:,.0f}")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


def render_funding_cumulative(report: TradeReport, out_path: Path) -> None:
    events = sorted(report.funding_events, key=lambda e: e.timestamp)

    fig, ax = plt.subplots(figsize=(10, 4), dpi=150)

    if not events:
        ax.text(0.5, 0.5, "No funding events in window", ha="center", va="center",
                transform=ax.transAxes, fontsize=13, color=GRAY)
        ax.set_xticks([])
        ax.set_yticks([])
        fig.savefig(out_path, bbox_inches="tight")
        plt.close(fig)
        return

    xs = [e.timestamp for e in events]
    cumulative_cost: list[float] = []
    running = Decimal("0")
    for e in events:
        running += -e.amount   # flip sign to cost
        cumulative_cost.append(float(running))

    ax.fill_between(xs, cumulative_cost, alpha=0.3, color=RED)
    ax.plot(xs, cumulative_cost, color=RED, linewidth=2)
    ax.set_ylabel("Cumulative funding paid (USD)", fontsize=11)
    ax.set_title("Funding bled over the hold", fontsize=13, color=TEXT)
    ax.yaxis.set_major_formatter(lambda v, _: f"${v:,.0f}")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
