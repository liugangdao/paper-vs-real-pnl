"""
Domain types for the paper-vs-real-pnl tool.

Sign conventions follow a two-stage pipeline:

1. Raw exchange conventions (FundingEvent.amount, Fill.fee_paid): positive =
   trader received, negative = trader paid. These match what the Hyperliquid
   Info API returns and are preserved verbatim.

2. Cost conventions (CostBreakdown.fees, CostBreakdown.funding,
   CostBreakdown.slippage_*): positive = the component *eats* paper PnL. The
   conversion from raw to cost is the job of the compute layer — funding
   amounts flip sign (compute_funding_cost), fees are already signed correctly
   at source, slippage is computed as a cost directly.

The invariant `paper_pnl − CostBreakdown.total_* = real_pnl_*` holds only when
all three cost components share the cost convention.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal


@dataclass(frozen=True)
class Fill:
    timestamp: datetime
    price: Decimal
    size: Decimal
    side: Literal["buy", "sell"]
    is_maker: bool
    fee_paid: Decimal   # Signed: negative if maker rebate received

    @property
    def signed_size(self) -> Decimal:
        return self.size if self.side == "buy" else -self.size

    @property
    def notional(self) -> Decimal:
        return self.price * self.size


@dataclass(frozen=True)
class FundingEvent:
    timestamp: datetime
    amount: Decimal     # Signed: positive = trader received, negative = trader paid


@dataclass(frozen=True)
class TradeWindow:
    wallet: str
    asset: str          # e.g., "BTC"
    start: datetime
    end: datetime


@dataclass(frozen=True)
class CostBreakdown:
    fees: Decimal
    funding: Decimal          # Cost convention (see module docstring): positive = net paid; sign-flipped from FundingEvent.amount by compute_funding_cost.
    slippage_mid: Decimal
    slippage_low: Decimal
    slippage_high: Decimal

    @property
    def total_mid(self) -> Decimal:
        return self.fees + self.funding + self.slippage_mid

    @property
    def total_low(self) -> Decimal:
        return self.fees + self.funding + self.slippage_low

    @property
    def total_high(self) -> Decimal:
        return self.fees + self.funding + self.slippage_high


@dataclass(frozen=True)
class TradeReport:
    window: TradeWindow
    entry_fills: tuple[Fill, ...]
    exit_fills: tuple[Fill, ...]
    funding_events: tuple[FundingEvent, ...]
    costs: CostBreakdown
    paper_pnl: Decimal
    real_pnl_mid: Decimal
    real_pnl_low: Decimal
    real_pnl_high: Decimal
