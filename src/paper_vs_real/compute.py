from decimal import Decimal

from paper_vs_real.types import Fill


def compute_fees(fills: list[Fill]) -> Decimal:
    """
    Sum of signed fees. Positive = trader paid net; negative = trader received net rebate.
    Relies on Fill.fee_paid being pre-signed by the exchange (maker rebates come through as negative).
    """
    if not fills:
        return Decimal("0")
    return sum((f.fee_paid for f in fills), start=Decimal("0"))
