# paper-vs-real-pnl

Audit a public Hyperliquid trade's real PnL after all friction costs (fees, funding, slippage).

Used to generate the numbers for the [Paper PnL vs Real](https://basiscalc.xyz/guides/) series on basiscalc.xyz.

## Install

```bash
pip install -e ".[dev]"
```

## Usage

```bash
python -m paper_vs_real --wallet 0x... --from 2026-03-01T00:00:00Z --to 2026-03-05T00:00:00Z --asset BTC
```

See the series for full methodology.
