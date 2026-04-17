import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx

from paper_vs_real.types import Fill, FundingEvent, TradeWindow

INFO_URL = "https://api.hyperliquid.xyz/info"
CAPTURE_ENV = "PAPER_VS_REAL_CAPTURE_DIR"


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
