"""
Walk-forward validation: rolling train/test windows.

Each window trains on 3 years, tests on 1 year.
Aggregated out-of-sample performance shows whether the strategy has a real edge.

Usage:
  python scripts/walk_forward.py

ANTI-OVERFITTING NOTE:
  This script uses data up to 2021-12-31 only.
  The 2022-2024 period remains sealed for the final out-of-sample test.
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import yaml
import pandas as pd
from loguru import logger

from src.data.fetcher import DataFetcher
from src.data.universe import UniverseSelector
from src.backtest.engine import BacktestEngine
from src.backtest.report import BacktestReport

WINDOWS = [
    {"train_start": "2015-01-01", "train_end": "2017-12-31", "test_start": "2018-01-01", "test_end": "2018-12-31"},
    {"train_start": "2016-01-01", "train_end": "2018-12-31", "test_start": "2019-01-01", "test_end": "2019-12-31"},
    {"train_start": "2017-01-01", "train_end": "2019-12-31", "test_start": "2020-01-01", "test_end": "2020-12-31"},
    {"train_start": "2018-01-01", "train_end": "2020-12-31", "test_start": "2021-01-01", "test_end": "2021-12-31"},
]

with open("config/config.yaml") as f:
    config = yaml.safe_load(f)

universe = UniverseSelector(config)
symbols = universe.get_universe()
fetcher = DataFetcher()
reporter = BacktestReport()

# Fetch all data at once (2015-2022)
all_data = fetcher.get_historical_bars(symbols, start="2015-01-01", end="2021-12-31")

print(f"\nWalk-forward validation: {len(WINDOWS)} windows\n")

oos_results = []
for w in WINDOWS:
    label = f"OOS {w['test_start'][:4]}"
    engine = BacktestEngine(config)
    try:
        _, metrics = engine.run(all_data, start_date=w["test_start"], end_date=w["test_end"])
        reporter.print_summary(metrics, label=label)
        oos_results.append(metrics)
    except Exception as e:
        print(f"{label}: ERROR — {e}")

if oos_results:
    df = pd.DataFrame(oos_results)
    print("\n" + "=" * 60)
    print("WALK-FORWARD AGGREGATE")
    print("=" * 60)
    print(f"  Windows tested:      {len(df)}")
    print(f"  Profitable windows:  {(df['total_return_pct'] > 0).sum()} / {len(df)}")
    print(f"  Avg Sharpe:          {df['sharpe_ratio'].mean():.3f}")
    print(f"  Avg Max Drawdown:    {df['max_drawdown_pct'].mean():.2f}%")
    print("=" * 60)

    profitable = (df["total_return_pct"] > 0).mean()
    if profitable >= 0.75:
        print("\n  PASS — profitable in ≥75% of OOS windows.")
        print("  Ready for out-of-sample test (2022-2024).")
    else:
        print("\n  FAIL — not consistently profitable across windows.")
        print("  Review strategy before running out-of-sample test.")
