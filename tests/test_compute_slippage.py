from decimal import Decimal
from datetime import datetime, timedelta, timezone

from paper_vs_real.types import Fill
from paper_vs_real.compute import compute_slippage, SlippageResult


def _fill(price: str, size: str, side: str, ts_offset_s: int = 0) -> Fill:
    ts = datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc) + timedelta(seconds=ts_offset_s)
    return Fill(timestamp=ts, price=Decimal(price), size=Decimal(size),
                side=side, is_maker=False, fee_paid=Decimal("0"))


def _candle(minute_offset: int, open_: str, close: str) -> dict:
    ts = datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc) + timedelta(minutes=minute_offset)
    return {"time": ts, "open": Decimal(open_), "close": Decimal(close),
            "high": Decimal(close), "low": Decimal(open_), "volume": Decimal("1")}


def test_buy_above_mid_yields_positive_slippage_cost():
    # Trader bought at 65100 when mid ≈ 65005 (TWAP of closes 65000, 65010)
    # signed_size = +100; slippage_mid = (65100 − 65005) × 100 = 9500
    fills = [_fill("65100", "100", "buy")]
    candles = [_candle(-1, "64990", "65000"), _candle(0, "65000", "65010")]
    result = compute_slippage(fills, candles)
    assert result.mid == Decimal("9500")
    assert result.low == Decimal("7600")
    assert result.high == Decimal("11400")


def test_sell_below_mid_yields_positive_slippage_cost():
    # Trader sold at 64900 when mid ≈ 65005
    # signed_size = −100; slippage_mid = (64900 − 65005) × −100 = +10500
    fills = [_fill("64900", "100", "sell")]
    candles = [_candle(-1, "64990", "65000"), _candle(0, "65000", "65010")]
    result = compute_slippage(fills, candles)
    assert result.mid == Decimal("10500")


def test_multiple_fills_summed():
    fills = [_fill("65100", "50", "buy"), _fill("65050", "50", "buy")]
    candles = [_candle(-1, "64990", "65000"), _candle(0, "65000", "65010")]
    result = compute_slippage(fills, candles)
    # Both fills' TWAP mid = 65005
    # f1 slip = (65100 − 65005) × 50 = 4750; f2 slip = (65050 − 65005) × 50 = 2250
    assert result.mid == Decimal("7000")


def test_slippage_result_fields():
    r = SlippageResult(mid=Decimal("100"), low=Decimal("80"), high=Decimal("120"))
    assert r.mid == Decimal("100")
    assert r.low == Decimal("80")
    assert r.high == Decimal("120")


def test_no_fills_returns_zeros():
    result = compute_slippage([], [])
    assert result.mid == Decimal("0")
    assert result.low == Decimal("0")
    assert result.high == Decimal("0")
