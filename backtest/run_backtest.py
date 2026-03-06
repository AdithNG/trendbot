"""
Run a backtest and print a performance summary.

Usage:
  # Training period (default in config.yaml: 2015-2019)
  python backtest/run_backtest.py

  # Override date range (use for out-of-sample test 2022-2024)
  python backtest/run_backtest.py --start 2022-01-01 --end 2024-12-31

  # Save HTML chart
  python backtest/run_backtest.py --html

ANTI-OVERFITTING WORKFLOW:
  1. Develop on training period (2015-2019)
  2. Run robustness check:   python scripts/robustness_check.py
  3. Walk-forward:           python scripts/walk_forward.py
  4. ONE final OOS test:     python backtest/run_backtest.py --start 2022-01-01 --end 2024-12-31
"""

import os
import sys
import argparse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import yaml
from loguru import logger

from src.data.fetcher import DataFetcher
from src.data.universe import UniverseSelector
from src.backtest.engine import BacktestEngine
from src.backtest.report import BacktestReport

parser = argparse.ArgumentParser(description="Run backtest")
parser.add_argument("--start", default=None, help="Start date YYYY-MM-DD (overrides config)")
parser.add_argument("--end", default=None, help="End date YYYY-MM-DD (overrides config)")
parser.add_argument("--html", action="store_true", help="Save HTML chart to backtest/results/")
args = parser.parse_args()

with open("config/config.yaml") as f:
    config = yaml.safe_load(f)

start = args.start or config["backtest"]["start_date"]
end = args.end or config["backtest"]["end_date"]

print(f"\nBacktest: {start} → {end}")
print(f"Universe: {config['universe']['max_symbols']} symbols")
print(f"Capital:  ${config['backtest']['initial_capital']:,}")

universe = UniverseSelector(config)
symbols = universe.get_universe()

fetcher = DataFetcher()
logger.info(f"Fetching data for {len(symbols)} symbols ...")
price_data = fetcher.get_historical_bars(symbols, start=start, end=end)

if not price_data:
    print("No data fetched. Check internet connection.")
    sys.exit(1)

engine = BacktestEngine(config)
portfolio, metrics = engine.run(price_data, start_date=start, end_date=end)

reporter = BacktestReport()
reporter.print_summary(metrics)

if args.html:
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    html_path = f"backtest/results/backtest_{start[:4]}_{end[:4]}_{ts}.html"
    reporter.save_html(portfolio, html_path)
