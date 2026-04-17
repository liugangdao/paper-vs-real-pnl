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
    funding: Decimal          # Signed; positive means trader paid out net, negative means received
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
