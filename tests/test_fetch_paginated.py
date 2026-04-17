"""
Tests for fetch_fills_paginated's recursive-bisection logic.

The HyperliquidClient is mocked to simulate 2000-fill caps and rate limiting.
Real sleep is patched to 0 to keep tests fast.
"""
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest

from paper_vs_real.fetch import (
    fetch_fills_paginated, FILL_BATCH_CAP, HyperliquidClient
)


def _raw_fill(
    coin: str = "ETH",
    time_ms: int = 1700000000000,
    side: str = "B",
    fee: str = "1.0",
    tid: int | None = None,
    start_pos: str = "0.0",
) -> dict:
    base = {
        "coin": coin,
        "px": "3000.0",
        "sz": "1.0",
        "side": side,
        "time": time_ms,
        "fee": fee,
        "crossed": True,
        "startPosition": start_pos,
        "oid": time_ms % 10000,
    }
    if tid is not None:
        base["tid"] = tid
    return base


def test_single_call_when_under_cap():
    client = MagicMock(spec=HyperliquidClient)
    client.post.return_value = [_raw_fill(tid=i) for i in range(500)]

    with patch("paper_vs_real.fetch.time.sleep"):
        fills = fetch_fills_paginated(
            client,
            wallet="0xabc",
            start=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end=datetime(2024, 1, 2, tzinfo=timezone.utc),
        )
    assert len(fills) == 500
    assert client.post.call_count == 1


def test_bisects_once_when_cap_hit_then_two_subcalls_under_cap():
    client = MagicMock(spec=HyperliquidClient)
    call_log = []

    def fake_post(body):
        call_log.append((body["startTime"], body["endTime"]))
        window = body["endTime"] - body["startTime"]
        if window > 50_000_000:   # first (full) call — one day = ~86.4M ms; each half ~43.2M ms
            return [_raw_fill(tid=i, time_ms=1700000000000 + i) for i in range(FILL_BATCH_CAP)]
        # Sub-call: use startTime to produce distinct tid ranges for each half
        offset = 10_000 if body["startTime"] == call_log[0][0] else 10_100
        return [_raw_fill(tid=offset + i, time_ms=1700000000000 + i) for i in range(100)]

    client.post.side_effect = fake_post

    with patch("paper_vs_real.fetch.time.sleep"):
        fills = fetch_fills_paginated(
            client,
            wallet="0xabc",
            start=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end=datetime(2024, 1, 2, tzinfo=timezone.utc),
        )

    assert client.post.call_count == 3  # 1 (cap) + 2 halves
    assert len(fills) == 200  # 100 from each half; cap was deduped away since halves had different tids


def test_dedupes_overlapping_fills():
    client = MagicMock(spec=HyperliquidClient)

    def fake_post(body):
        # Simulate: both halves return fills including a shared boundary tid
        if body["endTime"] - body["startTime"] > 1_000_000:
            return [_raw_fill(tid=i, time_ms=1700000000000 + i) for i in range(FILL_BATCH_CAP)]
        return [_raw_fill(tid=i, time_ms=1700000000000 + i) for i in range(50, 150)]

    client.post.side_effect = fake_post

    with patch("paper_vs_real.fetch.time.sleep"):
        fills = fetch_fills_paginated(
            client,
            wallet="0xabc",
            start=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end=datetime(2024, 1, 2, tzinfo=timezone.utc),
        )

    # Both halves returned tids 50-149 (overlapping). After dedupe: 100 unique fills.
    assert len(fills) == 100


def test_respects_request_delay():
    client = MagicMock(spec=HyperliquidClient)
    client.post.return_value = [_raw_fill(tid=i) for i in range(10)]

    with patch("paper_vs_real.fetch.time.sleep") as mock_sleep:
        fetch_fills_paginated(
            client,
            wallet="0xabc",
            start=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end=datetime(2024, 1, 2, tzinfo=timezone.utc),
            request_delay_s=0.7,
        )
    mock_sleep.assert_called_once_with(0.7)


def test_filters_by_asset():
    client = MagicMock(spec=HyperliquidClient)
    client.post.return_value = [
        _raw_fill(coin="ETH", tid=1),
        _raw_fill(coin="BTC", tid=2),
        _raw_fill(coin="ETH", tid=3),
    ]
    with patch("paper_vs_real.fetch.time.sleep"):
        fills = fetch_fills_paginated(
            client,
            wallet="0xabc",
            start=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end=datetime(2024, 1, 2, tzinfo=timezone.utc),
            asset="ETH",
        )
    assert len(fills) == 2


def test_split_entry_exit_flag():
    client = MagicMock(spec=HyperliquidClient)
    client.post.return_value = [
        _raw_fill(tid=1, start_pos="0"),   # entry
        _raw_fill(tid=2, start_pos="10"),  # exit
        _raw_fill(tid=3, start_pos="0"),   # entry
    ]
    with patch("paper_vs_real.fetch.time.sleep"):
        entry, exit_ = fetch_fills_paginated(
            client,
            wallet="0xabc",
            start=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end=datetime(2024, 1, 2, tzinfo=timezone.utc),
            split_entry_exit=True,
        )
    assert len(entry) == 2
    assert len(exit_) == 1


def test_bottoms_out_at_min_window_without_infinite_loop():
    """
    Pathological input: a single millisecond with >2000 fills.
    Should stop bisecting and return the truncated result without recursing forever.
    """
    client = MagicMock(spec=HyperliquidClient)
    client.post.return_value = [_raw_fill(tid=i) for i in range(FILL_BATCH_CAP)]

    with patch("paper_vs_real.fetch.time.sleep"):
        fills = fetch_fills_paginated(
            client,
            wallet="0xabc",
            start=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            end=datetime(2024, 1, 1, 12, 0, 0, 1_000, tzinfo=timezone.utc),  # 1ms window
            min_window_ms=1000,
        )
    assert len(fills) == FILL_BATCH_CAP
    # Exactly 1 API call since window is already at/below min_window_ms
    assert client.post.call_count == 1
