from decimal import Decimal

from paper_vs_real.types import Fill, FundingEvent


def compute_fees(fills: list[Fill]) -> Decimal:
    """
    Sum of signed fees. Positive = trader paid net; negative = trader received net rebate.
    Relies on Fill.fee_paid being pre-signed by the exchange (maker rebates come through as negative).
    """
    if not fills:
        return Decimal("0")
    return sum((f.fee_paid for f in fills), start=Decimal("0"))


def compute_funding_cost(events: list[FundingEvent]) -> Decimal:
    """
    Convert the exchange's signed funding amounts (positive=received, negative=paid)
    into a single 'cost' figure where positive = trader bled money to funding.

    The negation aligns funding with fees and slippage: all three should be positive
    when they reduce paper PnL, making paper_pnl - total = real_pnl straightforward.
    """
    if not events:
        return Decimal("0")
    raw_sum = sum((e.amount for e in events), start=Decimal("0"))
    return -raw_sum
