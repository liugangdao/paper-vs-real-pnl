import json
from pathlib import Path
from unittest.mock import patch

import pytest

from paper_vs_real.cli import run


FIXTURES = Path(__file__).parent / "fixtures"


@patch("paper_vs_real.cli.HyperliquidClient")
def test_run_produces_json_and_md(mock_client_cls, tmp_path):
    fills = json.loads((FIXTURES / "sample_fills_response.json").read_text())
    funding = json.loads((FIXTURES / "sample_funding_response.json").read_text())
    candles = json.loads((FIXTURES / "sample_candles_response.json").read_text())

    def fake_post(body):
        t = body["type"]
        if t == "userFills":
            return fills
        if t == "userFunding":
            return funding
        if t == "candleSnapshot":
            return candles
        raise ValueError(f"unexpected {t}")

    client_instance = mock_client_cls.return_value
    client_instance.post.side_effect = fake_post

    out_dir = tmp_path / "out"
    run(
        wallet="0xabc",
        asset="BTC",
        start_iso="2025-03-01T00:00:00Z",
        end_iso="2025-03-05T00:00:00Z",
        paper_pnl="300000",
        out_dir=out_dir,
    )

    assert (out_dir / "report.json").exists()
    assert (out_dir / "report.md").exists()
    obj = json.loads((out_dir / "report.json").read_text())
    assert obj["wallet"] == "0xabc"
    assert obj["asset"] == "BTC"
    assert "paper_pnl" in obj
    assert "real_pnl" in obj
