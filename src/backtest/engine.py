from __future__ import annotations

import pandas as pd
import vectorbt as vbt
from loguru import logger

from src.signals.indicators import compute_indicators
from src.signals.generator import SignalGenerator


class BacktestEngine:
    """
    Runs a vectorised backtest over a universe of symbols using vectorbt.

    The entry and exit boolean arrays are produced by SignalGenerator.entry_mask()
    and SignalGenerator.exit_mask() — the exact same logic used in the live bot.
    This prevents backtest-to-live divergence.
    """

    def __init__(self, config: dict):
        self.config = config
        self.sg = SignalGenerator(config["strategy"])

    def run(
        self,
        price_data: dict[str, pd.DataFrame],
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> tuple[vbt.Portfolio, dict]:
        """
        Args:
            price_data: {symbol: OHLCV DataFrame} from DataFetcher.
            start_date: Optional ISO date string to slice data (for train/OOS split).
            end_date:   Optional ISO date string to slice data.

        Returns:
            (portfolio, metrics) where metrics is a plain dict for easy looping.
        """
        all_closes: dict[str, pd.Series] = {}
        all_entries: dict[str, pd.Series] = {}
        all_exits: dict[str, pd.Series] = {}

        for symbol, df in price_data.items():
            df = compute_indicators(df, self.config["strategy"])
            df = df.dropna()

            if df.empty:
                logger.warning(f"Skipping {symbol}: no data after dropna()")
                continue

            # Slice to date range if provided
            if start_date:
                df = df[df.index >= pd.Timestamp(start_date)]
            if end_date:
                df = df[df.index <= pd.Timestamp(end_date)]

            if len(df) < self.config["strategy"]["slow_ema"] + 5:
                logger.warning(f"Skipping {symbol}: insufficient data ({len(df)} bars)")
                continue

            all_closes[symbol] = df["close"]
            all_entries[symbol] = self.sg.entry_mask(df)
            all_exits[symbol] = self.sg.exit_mask(df)

        if not all_closes:
            raise ValueError("No valid symbols to backtest.")

        closes = pd.DataFrame(all_closes)
        entries_df = pd.DataFrame(all_entries)
        exits_df = pd.DataFrame(all_exits)

        portfolio = vbt.Portfolio.from_signals(
            close=closes,
            entries=entries_df,
            exits=exits_df,
            init_cash=self.config["backtest"]["initial_capital"],
            fees=self.config["backtest"]["commission_pct"],
            freq="D",
        )

        metrics = self._extract_metrics(portfolio)
        return portfolio, metrics

    def _extract_metrics(self, portfolio: vbt.Portfolio) -> dict:
        stats = portfolio.stats()
        return {
            "total_return_pct": float(stats.get("Total Return [%]", 0)),
            "annualized_return_pct": float(stats.get("Annualized Return [%]", 0)),
            "sharpe_ratio": float(stats.get("Sharpe Ratio", 0)),
            "sortino_ratio": float(stats.get("Sortino Ratio", 0)),
            "max_drawdown_pct": float(stats.get("Max Drawdown [%]", 0)),
            "win_rate_pct": float(stats.get("Win Rate [%]", 0)),
            "total_trades": int(stats.get("Total Trades", 0)),
            "profit_factor": float(stats.get("Profit Factor", 0) or 0),
        }
