from __future__ import annotations

import pandas as pd
import yfinance as yf
from loguru import logger

# Fallback list of highly liquid S&P 500 stocks if Wikipedia fetch fails
FALLBACK_UNIVERSE = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "BRK-B",
    "JPM", "JNJ", "V", "PG", "MA", "HD", "AVGO", "MRK", "COST", "PEP",
    "XOM", "LLY",
]


class UniverseSelector:
    """
    Builds the trading universe from the S&P 500, filtered by liquidity.
    The list is re-fetched at most once per day (cached in memory).
    """

    def __init__(self, config: dict):
        self.config = config["universe"]
        self._cache: list[str] = []
        self._cache_date: str = ""

    def get_universe(self) -> list[str]:
        from datetime import date
        today = date.today().isoformat()
        if self._cache and self._cache_date == today:
            return self._cache

        symbols = self._fetch_sp500()
        filtered = self._filter_by_liquidity(symbols)
        self._cache = filtered
        self._cache_date = today
        logger.info(f"Universe updated: {len(filtered)} symbols")
        return filtered

    def _fetch_sp500(self) -> list[str]:
        try:
            tables = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
            df = tables[0]
            symbols = df["Symbol"].str.replace(".", "-", regex=False).tolist()
            logger.debug(f"Fetched {len(symbols)} S&P 500 symbols from Wikipedia")
            return symbols
        except Exception as e:
            logger.warning(f"Wikipedia fetch failed ({e}), using fallback universe")
            return FALLBACK_UNIVERSE

    def _filter_by_liquidity(self, symbols: list[str]) -> list[str]:
        max_symbols = self.config.get("max_symbols", 20)
        min_vol = self.config.get("min_avg_volume", 5_000_000)

        try:
            from datetime import date, timedelta
            end = date.today().isoformat()
            start = (date.today() - timedelta(days=45)).isoformat()

            data = yf.download(
                tickers=symbols[:100],  # Limit to avoid rate limits
                start=start,
                end=end,
                interval="1d",
                group_by="ticker",
                auto_adjust=True,
                progress=False,
                threads=True,
            )

            is_multi = isinstance(data.columns, pd.MultiIndex)
            vol_scores: dict[str, float] = {}
            for sym in symbols[:100]:
                try:
                    if is_multi:
                        vol = data.xs(sym, axis=1, level=1)["Volume"].mean()
                    else:
                        vol = data["Volume"].mean()
                    if vol >= min_vol:
                        vol_scores[sym] = vol
                except (KeyError, TypeError):
                    pass

            sorted_syms = sorted(vol_scores, key=vol_scores.get, reverse=True)

            if not sorted_syms:
                logger.warning("Liquidity filter returned 0 symbols, using fallback universe")
                return FALLBACK_UNIVERSE[:max_symbols]

            return sorted_syms[:max_symbols]

        except Exception as e:
            logger.warning(f"Liquidity filter failed ({e}), using top {max_symbols} of fallback")
            return FALLBACK_UNIVERSE[:max_symbols]
