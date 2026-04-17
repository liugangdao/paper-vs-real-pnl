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
    Waterfall: Paper claim → [Unrealized melt] → [Realized on chain] → −Fees → −Funding → [−Slippage] → Net after friction.

    Sections are conditionally included:
    - "Unrealized melt" and "Realized on chain" appear only when realized_pnl_from_chain
      is meaningfully different from paper_pnl (threshold: abs diff > 1% of paper_pnl).
    - Slippage appears only when costs.slippage_mid is nonzero.
    """
    c = report.costs
    paper = report.paper_pnl
    realized = report.realized_pnl_from_chain

    show_realized = realized > 0 and abs(paper - realized) / paper > Decimal("0.01")
    show_slip = c.slippage_mid != 0

    # Build segments: (label, value, is_absolute)
    # is_absolute=True means the bar height is the absolute value (paper claim, realized marker, final bar)
    # is_absolute=False means it's a delta (negative = red downward bar)
    segments: list[tuple[str, float, bool]] = []
    segments.append(("Paper claim", float(paper), True))
    if show_realized:
        segments.append(("Unrealized\nmelt", float(realized - paper), False))
        segments.append(("Realized\non chain", float(realized), True))
    segments.append(("Fees", -float(c.fees), False))
    segments.append(("Funding", -float(c.funding), False))
    if show_slip:
        segments.append(("Slippage", -float(c.slippage_mid), False))

    base_for_final = float(realized) if show_realized else float(paper)
    final_real = base_for_final - float(c.fees) - float(c.funding) - (float(c.slippage_mid) if show_slip else 0.0)
    segments.append(("Net after\nfriction", final_real, True))

    labels = [s[0] for s in segments]
    values = [s[1] for s in segments]
    is_absolute = [s[2] for s in segments]

    # Build cumulative running total for positioning delta bars
    cum: list[float] = []
    for i, (val, absol) in enumerate(zip(values, is_absolute)):
        if absol:
            cum.append(val)
        else:
            cum.append(cum[-1] + val)

    fig, ax = plt.subplots(figsize=(12, 5), dpi=150)
    x = list(range(len(labels)))

    for i, (label, val, absol) in enumerate(zip(labels, values, is_absolute)):
        if i == 0:
            # Paper claim — green anchor
            ax.bar(i, val, color=EMERALD, edgecolor=TEXT)
        elif i == len(segments) - 1:
            # Net after friction — gray final bar
            ax.bar(i, val, color=GRAY, edgecolor=TEXT)
        elif absol:
            # "Realized on chain" absolute marker — muted gray
            ax.bar(i, val, color=GRAY, edgecolor=TEXT, alpha=0.7)
        else:
            # Delta bar — red downward bar floating from previous cumulative
            bottom = cum[i - 1] + val   # bottom of the downward bar = cum[i] (after delta)
            ax.bar(i, -val, bottom=bottom, color=RED, edgecolor=TEXT)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
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
