from __future__ import annotations

from loguru import logger

# Top 20 most liquid S&P 500 stocks by average daily volume.
# This list is stable — these names rarely change and all clear 5M+ shares/day.
UNIVERSE = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "BRK-B",
    "JPM", "JNJ", "V", "PG", "MA", "HD", "AVGO", "MRK", "COST", "PEP",
    "XOM", "LLY",
]


class UniverseSelector:
    """
    Returns a fixed list of the 20 most liquid S&P 500 stocks.

    The previous approach (Wikipedia scrape + per-symbol volume filter) was
    too slow (~2 min) and hit Yahoo Finance rate limits every cycle.
    The hardcoded list is stable enough for daily EMA momentum trading.
    """

    def __init__(self, config: dict):
        self.config = config["universe"]

    def get_universe(self) -> list[str]:
        max_symbols = self.config.get("max_symbols", 20)
        symbols = UNIVERSE[:max_symbols]
        logger.debug(f"Universe: {len(symbols)} symbols")
        return symbols
