# paper-vs-real-pnl

Audit a public Hyperliquid trade's real PnL after all friction costs —
fees (with signed maker rebates), funding, and slippage against a TWAP
mid-price approximation.

Powers the [**Paper PnL vs Real**](https://basiscalc.xyz/guides/paper-vs-real-pnl-wynn/)
series on basiscalc.xyz.

## Install

```bash
git clone https://github.com/liugangdao/paper-vs-real-pnl.git
cd paper-vs-real-pnl
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Usage

```bash
python -m paper_vs_real \
  --wallet 0xYOURWALLET \
  --asset BTC \
  --from 2026-03-01T00:00:00Z \
  --to 2026-03-05T00:00:00Z \
  --paper-pnl 50000 \
  --out outputs/
```

Produces `report.json`, `report.md`, `waterfall.png`, `funding.png` in `outputs/`.

## Methodology (short)

- **Fees**: `sum(signed fee per fill)` — maker rebates are negative.
- **Funding**: `−sum(userFunding.amount)` — sign flipped so positive = trader paid.
- **Slippage**: `sum((fill_price − TWAP_mid) × signed_size)`; TWAP over a 60s
  window around each fill; reported with a ±20% error band.
- **Scope**: audits one specific trade on one wallet; does not account for
  hedges on other venues or other wallets.

Full write-up in the linked article.

## Tests

```bash
pytest
```

## License

MIT.
