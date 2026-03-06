from __future__ import annotations

import yfinance as yf
import pandas as pd
from loguru import logger


class DataFetcher:
    """
    Fetches historical OHLCV data via yfinance.
    Used for backtesting and for warming up indicators before the live trading loop.
    """

    def get_historical_bars(
        self,
        symbols: list[str],
        start: str,
        end: str,
        interval: str = "1d",
    ) -> dict[str, pd.DataFrame]:
        """
        Returns {symbol: OHLCV DataFrame} with lowercase column names.
        Columns: open, high, low, close, volume
        """
        if not symbols:
            return {}

        logger.debug(f"Fetching {len(symbols)} symbols from {start} to {end} [{interval}]")

        data = yf.download(
            tickers=symbols,
            start=start,
            end=end,
            interval=interval,
            group_by="ticker",
            auto_adjust=True,
            progress=False,
            threads=True,
        )

        result: dict[str, pd.DataFrame] = {}

        if data.empty:
            logger.warning("yfinance returned empty data")
            return result

        # New yfinance (>=0.2.x) returns (field, ticker) MultiIndex columns for
        # multi-symbol downloads. Single-symbol downloads return flat columns.
        is_multi = isinstance(data.columns, pd.MultiIndex)

        for sym in symbols:
            try:
                if is_multi:
                    df = data.xs(sym, axis=1, level=1).copy()
                else:
                    df = data.copy()
                df.columns = [c.lower() for c in df.columns]
                df = df.drop(columns=["adj close"], errors="ignore")
                df = df.dropna()
                if not df.empty:
                    result[sym] = df
            except (KeyError, TypeError):
                logger.warning(f"No data returned for {sym}")

        logger.debug(f"Got data for {len(result)}/{len(symbols)} symbols")
        return result

    def get_warmup_bars(
        self,
        symbols: list[str],
        lookback_days: int = 120,
        interval: str = "1d",
    ) -> dict[str, pd.DataFrame]:
        """
        Fetches the last `lookback_days` calendar days of daily bars.
        Used to warm up indicators before the live trading loop starts.
        """
        from datetime import date, timedelta
        end = date.today().isoformat()
        start = (date.today() - timedelta(days=lookback_days)).isoformat()
        return self.get_historical_bars(symbols, start, end, interval)
