from dataclasses import dataclass
from datetime import timedelta
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


@dataclass(frozen=True)
class SlippageResult:
    mid: Decimal
    low: Decimal
    high: Decimal


def _twap_mid(fill_time, candles: list[dict], window_seconds: int = 60) -> Decimal:
    """
    Average of candle closes whose timestamps fall in [fill_time - window, fill_time + window].

    Default window is 60s per side — a deliberate deviation from the spec's stated ±30s (§4.1).
    The spec was written assuming 1-second price samples; with 1-minute candles, a ±30s window
    catches 0-1 candles depending on where the fill falls within the minute, making the result
    arbitrary. ±60s reliably brackets the fill with at least one candle on each side. The
    resulting approximation imprecision is absorbed by the ±20% error band mandated in §4.3.

    Falls back to the single nearest candle if the window catches nothing (data gaps).
    """
    lo = fill_time - timedelta(seconds=window_seconds)
    hi = fill_time + timedelta(seconds=window_seconds)
    in_window = [c for c in candles if lo <= c["time"] <= hi]
    if not in_window:
        nearest = min(candles, key=lambda c: abs((c["time"] - fill_time).total_seconds()))
        return nearest["close"]
    return sum((c["close"] for c in in_window), start=Decimal("0")) / Decimal(len(in_window))


def compute_slippage(
    fills: list[Fill],
    candles: list[dict],
    error_band: Decimal = Decimal("0.2"),
) -> SlippageResult:
    """
    Slippage cost = (fill_price − mid) × signed_size, summed across fills.
    Positive result = slippage ate paper PnL.

    TWAP mid is an approximation; we expose a ±20% band around the computed figure
    (spec §4.3) so the article can report a range rather than a false-precision number.

    WARNING — KNOWN METHODOLOGY LIMITATION:

    For HFT-style whales with sub-second execution, 1-minute candle closes are
    far too coarse as a mid-price proxy. The resulting slippage figure can be
    off by >100% or even flip sign (reporting a "favorable" slippage that is
    an artifact of candle mismatch, not real execution edge). Episode 1 of the
    series explicitly excludes slippage from its headline numbers for this
    reason; the article states this limitation in its methodology section.

    Future work: supplement with orderbook L2 snapshots or 1-second trade
    prints to get meaningful sub-minute mid-price approximation.
    """
    if not fills or not candles:
        return SlippageResult(mid=Decimal("0"), low=Decimal("0"), high=Decimal("0"))

    total = Decimal("0")
    for f in fills:
        mid = _twap_mid(f.timestamp, candles)
        total += (f.price - mid) * f.signed_size

    low = total * (Decimal("1") - error_band)
    high = total * (Decimal("1") + error_band)
    return SlippageResult(mid=total, low=low, high=high)
