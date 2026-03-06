"""
Robustness check: vary strategy parameters by ±20% and compare Sharpe ratios.

A robust strategy should produce similar results across nearby parameter values.
A fragile (overfit) strategy will only work at the "magic" combination.

Usage:
  python scripts/robustness_check.py

Output:
  Table of results for each parameter combination.
  Summary: median Sharpe, % profitable variants.
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import copy
import itertools

import yaml
import pandas as pd
from loguru import logger

from src.data.fetcher import DataFetcher
from src.data.universe import UniverseSelector
from src.backtest.engine import BacktestEngine

# -----------------------------------------------------------------------
# ANTI-OVERFITTING: Use training + validation data ONLY.
# Never use 2022-2024 (out-of-sample) here.
# -----------------------------------------------------------------------
TRAIN_START = "2015-01-01"
TRAIN_END = "2021-12-31"

PARAM_GRID = {
    "fast_ema":            [15, 18, 20, 22, 25],
    "slow_ema":            [40, 45, 50, 55, 60],
    "atr_stop_multiplier": [1.5, 2.0, 2.5],
}

with open("config/config.yaml") as f:
    base_config = yaml.safe_load(f)

logger.info("Fetching universe and price data for robustness check ...")
universe = UniverseSelector(base_config)
symbols = universe.get_universe()

fetcher = DataFetcher()
price_data = fetcher.get_historical_bars(symbols, start=TRAIN_START, end=TRAIN_END)

if not price_data:
    print("No price data fetched. Check internet connection and universe config.")
    sys.exit(1)

print(f"\nRunning robustness check on {len(symbols)} symbols, {TRAIN_START} to {TRAIN_END}")
print(f"Parameter grid: {sum(len(v) for v in PARAM_GRID.values())} total combinations\n")

results = []
keys = list(PARAM_GRID.keys())
for combo in itertools.product(*PARAM_GRID.values()):
    params = dict(zip(keys, combo))

    config = copy.deepcopy(base_config)
    for k, v in params.items():
        config["strategy"][k] = v

    try:
        engine = BacktestEngine(config)
        _, metrics = engine.run(price_data)
        results.append({**params, **metrics})
    except Exception as e:
        logger.warning(f"Combo {params} failed: {e}")

df = pd.DataFrame(results)
if df.empty:
    print("No results generated.")
    sys.exit(1)

df = df.sort_values("sharpe_ratio", ascending=False)

print(df[["fast_ema", "slow_ema", "atr_stop_multiplier",
          "sharpe_ratio", "total_return_pct", "max_drawdown_pct", "win_rate_pct"]].to_string(index=False))

median_sharpe = df["sharpe_ratio"].median()
pct_profitable = (df["total_return_pct"] > 0).mean() * 100

print(f"\n{'='*60}")
print(f"  Median Sharpe:        {median_sharpe:.3f}  (want > 0.5)")
print(f"  % Profitable combos:  {pct_profitable:.1f}%  (want > 70%)")
print(f"{'='*60}")

if median_sharpe > 0.5 and pct_profitable > 70:
    print("\n  PASS — strategy appears robust. Proceed to walk-forward test.")
else:
    print("\n  FAIL — strategy may be fragile. Review parameters before proceeding.")
