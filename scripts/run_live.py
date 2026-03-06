"""
Start the trading bot in LIVE mode (REAL MONEY).

WARNING: This script places REAL orders with REAL money.
Only run this after:
  1. Backtesting passes all three phases (train, robustness, out-of-sample)
  2. Paper trading ran for at least 4 weeks without critical errors

Requirements:
  - Set ALPACA_BASE_URL=https://api.alpaca.markets in .env
  - Set ALPACA_API_KEY and ALPACA_SECRET_KEY in .env

Usage:
  python scripts/run_live.py
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import yaml
from dotenv import load_dotenv
from loguru import logger

from src.bot.runner import BotRunner
from src.broker.alpaca_client import AlpacaClient
from src.utils.logger import setup_logging

load_dotenv()

with open("config/config.yaml") as f:
    config = yaml.safe_load(f)

setup_logging(config["logging"])

api_key = os.getenv("ALPACA_API_KEY")
secret_key = os.getenv("ALPACA_SECRET_KEY")
base_url = os.getenv("ALPACA_BASE_URL", "")

if not api_key or not secret_key:
    logger.error("Missing ALPACA_API_KEY or ALPACA_SECRET_KEY in .env")
    sys.exit(1)

if "paper" in base_url.lower():
    logger.error(
        "ALPACA_BASE_URL points to paper API but you are running run_live.py. "
        "Update .env to https://api.alpaca.markets for live trading."
    )
    sys.exit(1)

# Final confirmation prompt
print("\n" + "!" * 60)
print("  WARNING: LIVE TRADING — REAL MONEY WILL BE AT RISK")
print("!" * 60)
confirm = input("Type 'yes' to continue: ").strip().lower()
if confirm != "yes":
    print("Aborted.")
    sys.exit(0)

logger.info("Starting bot in LIVE mode")
broker = AlpacaClient(api_key=api_key, secret_key=secret_key, paper=False)
runner = BotRunner(config=config, broker=broker)
runner.start()
