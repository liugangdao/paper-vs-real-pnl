import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx

from paper_vs_real.types import Fill, FundingEvent, TradeWindow

INFO_URL = "https://api.hyperliquid.xyz/info"
CAPTURE_ENV = "PAPER_VS_REAL_CAPTURE_DIR"
FILL_BATCH_CAP = 2000


@dataclass
class HyperliquidClient:
    base_url: str = INFO_URL
    timeout: float = 30.0
    _client: httpx.Client = field(default=None, init=False, repr=False)

    def post(self, body: dict[str, Any]) -> Any:
        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout)
        resp = self._client.post(self.base_url, json=body)
        resp.raise_for_status()
        data = resp.json()

        capture_dir = os.environ.get(CAPTURE_ENV)
        if capture_dir:
            path = Path(capture_dir)
            path.mkdir(parents=True, exist_ok=True)
            (path / f"{body['type']}.json").write_text(json.dumps(data, indent=2))

        return data


def _fill_from_raw(raw: dict[str, Any]) -> Fill:
    side = "buy" if raw["side"] == "B" else "sell"
    return Fill(
        timestamp=datetime.fromtimestamp(raw["time"] / 1000, tz=timezone.utc),
        price=Decimal(raw["px"]),
        size=Decimal(raw["sz"]),
        side=side,
        is_maker=not raw["crossed"],
        fee_paid=Decimal(raw["fee"]),
    )


def fetch_fills(
    client: HyperliquidClient,
    wallet: str,
    window: TradeWindow | None = None,
    split_entry_exit: bool = False,
) -> list[Fill] | tuple[list[Fill], list[Fill]]:
    raw = client.post({"type": "userFills", "user": wallet})

    if window is not None:
        paired = [(r, _fill_from_raw(r)) for r in raw if r["coin"] == window.asset]
        paired = [(r, f) for r, f in paired if window.start <= f.timestamp <= window.end]
    else:
        paired = [(r, _fill_from_raw(r)) for r in raw]

    fills = [f for _, f in paired]

    if not split_entry_exit:
        return fills

    entry, exit_ = [], []
    for r, f in paired:
        if Decimal(str(r.get("startPosition", "0"))) == 0:
            entry.append(f)
        else:
            exit_.append(f)
    return entry, exit_


def fetch_fills_paginated(
    client: HyperliquidClient,
    wallet: str,
    start: datetime,
    end: datetime,
    asset: str | None = None,
    request_delay_s: float = 0.4,
    min_window_ms: int = 1000,
    split_entry_exit: bool = False,
) -> list[Fill] | tuple[list[Fill], list[Fill]]:
    """
    Retrieve all fills in [start, end] for the given wallet, bypassing the
    2000-fill single-call cap by recursively bisecting on time.

    The recursive bisection: if a call returns exactly FILL_BATCH_CAP fills,
    the window is presumed truncated; we split into two halves and recurse.

    Rate-limits itself to one request per `request_delay_s` seconds by
    sleeping before each API call (applied uniformly; the caller does not
    need to pre-delay).

    Dedupes by fill `tid` (trade id — Hyperliquid returns this per fill).
    When `tid` is absent, falls back to (time, oid) tuples.

    Returns the same shape as `fetch_fills`:
      - list[Fill] when split_entry_exit=False
      - tuple[list[Fill], list[Fill]] (entry, exit) when True
    """
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)

    raw_all: list[dict] = []
    _paginate_raw(client, wallet, start_ms, end_ms, request_delay_s, min_window_ms, raw_all)

    seen: set = set()
    unique: list[dict] = []
    for r in raw_all:
        key = r.get("tid", (r.get("time"), r.get("oid")))
        if key in seen:
            continue
        seen.add(key)
        unique.append(r)

    if asset is not None:
        unique = [r for r in unique if r.get("coin") == asset]

    fills = [_fill_from_raw(r) for r in unique]

    if not split_entry_exit:
        return fills

    entry: list[Fill] = []
    exit_: list[Fill] = []
    for r, f in zip(unique, fills, strict=True):
        if Decimal(str(r.get("startPosition", "0"))) == 0:
            entry.append(f)
        else:
            exit_.append(f)
    return entry, exit_


def _paginate_raw(
    client: HyperliquidClient,
    wallet: str,
    start_ms: int,
    end_ms: int,
    request_delay_s: float,
    min_window_ms: int,
    out: list[dict],
) -> None:
    time.sleep(request_delay_s)
    body = {
        "type": "userFillsByTime",
        "user": wallet,
        "startTime": start_ms,
        "endTime": end_ms,
    }
    raw = client.post(body)
    if len(raw) < FILL_BATCH_CAP:
        out.extend(raw)
        return
    # Possibly truncated
    window = end_ms - start_ms
    if window <= min_window_ms:
        # Cannot split further; accept truncation
        out.extend(raw)
        return
    mid = (start_ms + end_ms) // 2
    _paginate_raw(client, wallet, start_ms, mid, request_delay_s, min_window_ms, out)
    _paginate_raw(client, wallet, mid + 1, end_ms, request_delay_s, min_window_ms, out)


def fetch_funding(
    client: HyperliquidClient,
    wallet: str,
    start: datetime,
    end: datetime,
) -> list[FundingEvent]:
    body = {
        "type": "userFunding",
        "user": wallet,
        "startTime": int(start.timestamp() * 1000),
        "endTime": int(end.timestamp() * 1000),
    }
    raw = client.post(body)
    return [
        FundingEvent(
            timestamp=datetime.fromtimestamp(r["time"] / 1000, tz=timezone.utc),
            amount=Decimal(r["usdc"]),
        )
        for r in raw
    ]


def fetch_candles(
    client: HyperliquidClient,
    asset: str,
    start: datetime,
    end: datetime,
    interval: str = "1m",
) -> list[dict[str, Any]]:
    body = {
        "type": "candleSnapshot",
        "req": {
            "coin": asset,
            "interval": interval,
            "startTime": int(start.timestamp() * 1000),
            "endTime": int(end.timestamp() * 1000),
        },
    }
    raw = client.post(body)
    return [
        {
            "time": datetime.fromtimestamp(c["t"] / 1000, tz=timezone.utc),
            "open": Decimal(c["o"]),
            "close": Decimal(c["c"]),
            "high": Decimal(c["h"]),
            "low": Decimal(c["l"]),
            "volume": Decimal(c["v"]),
        }
        for c in raw
    ]
