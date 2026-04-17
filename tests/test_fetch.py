from decimal import Decimal
from datetime import datetime, timezone
import json
from pathlib import Path

import pytest
import respx
from httpx import Response

from paper_vs_real.fetch import (
    fetch_fills, fetch_funding, fetch_candles, HyperliquidClient
)
from paper_vs_real.types import TradeWindow

FIXTURES = Path(__file__).parent / "fixtures"


@respx.mock
def test_fetch_fills_parses_side_and_signed_fee():
    body = json.loads((FIXTURES / "sample_fills_response.json").read_text())
    respx.post("https://api.hyperliquid.xyz/info").mock(return_value=Response(200, json=body))

    client = HyperliquidClient()
    fills = fetch_fills(client, wallet="0xabc")

    assert len(fills) == 2
    assert fills[0].side == "buy"
    assert fills[0].is_maker is False
    assert fills[0].fee_paid == Decimal("1.30")
    assert fills[1].side == "sell"
    assert fills[1].is_maker is True
    assert fills[1].fee_paid == Decimal("-0.34")


@respx.mock
def test_fetch_fills_filters_by_window_and_asset():
    body = json.loads((FIXTURES / "sample_fills_response.json").read_text())
    respx.post("https://api.hyperliquid.xyz/info").mock(return_value=Response(200, json=body))

    window = TradeWindow(
        wallet="0xabc",
        asset="BTC",
        start=datetime(2025, 3, 1, tzinfo=timezone.utc),
        end=datetime(2025, 3, 5, tzinfo=timezone.utc),
    )
    entry, exit_ = fetch_fills(HyperliquidClient(), wallet="0xabc", window=window, split_entry_exit=True)
    assert len(entry) == 1
    assert entry[0].side == "buy"
    assert len(exit_) == 1
    assert exit_[0].side == "sell"


@respx.mock
def test_fetch_funding_returns_signed_events():
    body = json.loads((FIXTURES / "sample_funding_response.json").read_text())
    respx.post("https://api.hyperliquid.xyz/info").mock(return_value=Response(200, json=body))

    events = fetch_funding(
        HyperliquidClient(),
        wallet="0xabc",
        start=datetime(2026, 3, 1, tzinfo=timezone.utc),
        end=datetime(2026, 3, 5, tzinfo=timezone.utc),
    )
    assert len(events) == 2
    assert events[0].amount == Decimal("-50.0")
    assert events[1].amount == Decimal("-62.5")


@respx.mock
def test_fetch_fills_uses_dir_for_entry_exit_split():
    body = json.loads((FIXTURES / "sample_fills_response.json").read_text())
    respx.post("https://api.hyperliquid.xyz/info").mock(return_value=Response(200, json=body))

    window = TradeWindow(
        wallet="0xabc",
        asset="BTC",
        start=datetime(2025, 3, 1, tzinfo=timezone.utc),
        end=datetime(2025, 3, 5, tzinfo=timezone.utc),
    )
    entry, exit_ = fetch_fills(
        HyperliquidClient(), wallet="0xabc", window=window, split_entry_exit=True
    )
    assert len(entry) == 1
    assert entry[0].side == "buy"
    assert len(exit_) == 1
    assert exit_[0].side == "sell"


@respx.mock
def test_fetch_candles_returns_ohlcv():
    body = json.loads((FIXTURES / "sample_candles_response.json").read_text())
    respx.post("https://api.hyperliquid.xyz/info").mock(return_value=Response(200, json=body))

    candles = fetch_candles(
        HyperliquidClient(),
        asset="BTC",
        start=datetime(2026, 3, 1, tzinfo=timezone.utc),
        end=datetime(2026, 3, 1, 0, 5, tzinfo=timezone.utc),
        interval="1m",
    )
    assert len(candles) == 1
    assert candles[0]["open"] == Decimal("64990")
    assert candles[0]["close"] == Decimal("65010")
