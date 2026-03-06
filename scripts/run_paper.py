"""
Start the trading bot in PAPER mode (fake money, real market data).

Requirements:
  - Copy .env.example to .env
  - Set ALPACA_BASE_URL=https://paper-api.alpaca.markets in .env
  - Set ALPACA_API_KEY and ALPACA_SECRET_KEY in .env

Usage:
  python scripts/run_paper.py
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

is_paper = "paper" in base_url.lower()
if not is_paper:
    logger.error(
        "ALPACA_BASE_URL does not contain 'paper'. "
        "Use scripts/run_live.py for live trading, or update .env."
    )
    sys.exit(1)

logger.info("Starting bot in PAPER mode")
broker = AlpacaClient(api_key=api_key, secret_key=secret_key, paper=True)
runner = BotRunner(config=config, broker=broker)
runner.start()
