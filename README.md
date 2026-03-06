# TrendBot

An automated equity trading bot using an EMA momentum strategy, built on top of [Alpaca Markets](https://alpaca.markets) and [yfinance](https://github.com/ranaroussi/yfinance).

- Scans the top 20 most-liquid S&P 500 stocks every 5 minutes
- Buys on EMA(20/50) crossover + RSI + volume confirmation
- Sells on EMA cross-down or ATR-based trailing stop
- Hard daily loss limit to cap drawdowns
- Full vectorized backtest with anti-overfitting workflow

---

## Requirements

- Python 3.12+ (`python --version`)
- An [Alpaca](https://app.alpaca.markets) account (paper or live)

---

## Setup

```bash
# 1. Clone
git clone https://github.com/AdithNG/trendbot.git
cd trendbot

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure API keys
cp .env.example .env
# Edit .env and fill in ALPACA_API_KEY and ALPACA_SECRET_KEY
```

---

## Running the Bot

### Paper trading (recommended first)

```bash
python scripts/run_paper.py
```

**Run in the background** (no terminal window needed, survives closing VS Code):

```powershell
start pythonw scripts\run_paper.py
```

Watch logs live:
```powershell
Get-Content logs\trading_bot.log -Wait -Tail 50
```

Stop the bot:
```powershell
taskkill /f /im pythonw.exe
```

Requires `.env` with `ALPACA_BASE_URL=https://paper-api.alpaca.markets`.

### Live trading (real money)

```bash
python scripts/run_live.py
```

Requires `.env` with `ALPACA_BASE_URL=https://api.alpaca.markets`.
You will be prompted to confirm before any orders are placed.

---

## Backtesting

```bash
# Training period (2015-2019, defined in config)
python backtest/run_backtest.py

# Custom date range
python backtest/run_backtest.py --start 2022-01-01 --end 2024-12-31

# Save equity curve as HTML chart
python backtest/run_backtest.py --html
```

### Anti-overfitting workflow

The strategy is validated in three stages before touching live capital:

| Stage | Script | Data |
|-------|--------|------|
| 1. Design | `backtest/run_backtest.py` | 2015-2019 (training) |
| 2. Robustness | `scripts/robustness_check.py` | 2015-2021 (param grid) |
| 3. Walk-forward | `scripts/walk_forward.py` | 2015-2021 (rolling OOS) |
| 4. Final OOS | `backtest/run_backtest.py --start 2022-01-01 --end 2024-12-31` | 2022-2024 (sealed) |

Run stage 4 **once only**. Repeated OOS tests invalidate the out-of-sample guarantee.

---

## Configuration

All parameters live in [config/config.yaml](config/config.yaml):

```yaml
strategy:
  fast_ema: 20
  slow_ema: 50
  rsi_overbought: 65
  rsi_oversold: 35
  volume_confirmation_ratio: 1.5

risk:
  position_pct_of_portfolio: 0.25   # 25% per position
  max_open_positions: 4
  daily_loss_limit: 0.05            # halt if daily P&L < -5%
```

---

## Tests

```bash
pytest tests/ -v
```

Tests cover indicators, signal generation, and risk calculations. No Alpaca keys required.

---

## Project Structure

```
trendbot/
├── backtest/
│   ├── run_backtest.py       # Main backtest runner
│   └── results/              # HTML charts saved here
├── config/
│   └── config.yaml           # All strategy and risk parameters
├── scripts/
│   ├── run_paper.py          # Start paper trading
│   ├── run_live.py           # Start live trading
│   ├── robustness_check.py   # Parameter grid robustness test
│   └── walk_forward.py       # Rolling OOS validation
├── src/
│   ├── backtest/             # Vectorbt-based backtest engine
│   ├── bot/                  # BotRunner + PortfolioState
│   ├── broker/               # AlpacaClient wrapper
│   ├── data/                 # DataFetcher (yfinance) + UniverseSelector
│   ├── signals/              # Indicators + SignalGenerator
│   └── strategy/             # RiskManager
├── tests/                    # pytest test suite
├── .env.example              # API key template
└── requirements.txt
```

---

## Strategy Overview

**Entry** (all conditions required):
- EMA(20) crosses above EMA(50)
- Price is above EMA(50) (trend filter)
- RSI is between 35 and 65 (not overbought/oversold)
- Volume is 1.5x the 20-bar average (confirmation)

**Exit**:
- EMA(20) crosses below EMA(50), or
- ATR-based trailing stop activates after a 5% gain

**Position sizing**:
- 25% of portfolio per position (max 4 open positions)
- Falls back to fractional/notional orders for small accounts
