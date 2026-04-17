import json
from pathlib import Path
from unittest.mock import patch

from paper_vs_real.cli import run


FIXTURE = Path(__file__).parent / "fixtures" / "integration_trade.json"


@patch("paper_vs_real.fetch.time.sleep")
@patch("paper_vs_real.cli.HyperliquidClient")
def test_integration_episode_1_numbers_locked(mock_client_cls, mock_sleep, tmp_path):
    """
    Lock the Episode 1 target trade's numbers into an integration fixture.
    Any future change to compute.py, fetch.py, or the sign conventions that
    shifts these figures will fail this test and force a deliberate article update.
    """
    fixture = json.loads(FIXTURE.read_text())

    # Per-type call iterator (each successive call returns the next inner list)
    iterators = {
        t: iter(responses) for t, responses in fixture["api_responses"].items()
    }

    def fake_post(body):
        t = body["type"]
        try:
            return next(iterators[t])
        except (KeyError, StopIteration):
            # Sequential pagination terminates when result < FILL_BATCH_CAP; return empty if we're out
            return []

    mock_client_cls.return_value.post.side_effect = fake_post

    report = run(
        wallet=fixture["wallet"],
        asset=fixture["asset"],
        start_iso=fixture["window"]["start"],
        end_iso=fixture["window"]["end"],
        paper_pnl=fixture["paper_pnl"],
        out_dir=tmp_path,
    )

    expected = fixture["expected_report"]
    # Lock specific headline figures:
    assert str(report.paper_pnl) == expected["paper_pnl"], "paper_pnl drift"
    assert str(report.costs.fees) == expected["costs"]["fees"], "fees drift"
    assert str(report.costs.funding) == expected["costs"]["funding"], "funding drift"
    assert str(report.realized_pnl_from_chain) == expected["realized_pnl_from_chain"], "realized_pnl drift"
