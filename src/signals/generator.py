from __future__ import annotations

from enum import Enum

import pandas as pd
from loguru import logger


class Signal(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class SignalGenerator:
    """
    Translates indicator values into BUY / SELL / HOLD signals.

    IMPORTANT: The entry/exit logic here must exactly match the boolean arrays
    produced in BacktestEngine.run() so that live and backtest behaviour are
    identical.
    """

    def __init__(self, config: dict):
        self.config = config

    def get_signal(self, df: pd.DataFrame, has_position: bool) -> Signal:
        """
        Evaluates the most recent (last) row of an indicator-enriched DataFrame.

        Args:
            df: DataFrame with columns produced by compute_indicators().
            has_position: True if we currently hold this symbol.

        Returns:
            Signal enum value.
        """
        if df.empty or df[["ema_fast", "ema_slow", "atr", "rsi"]].iloc[-1].isna().any():
            return Signal.HOLD

        row = df.iloc[-1]

        # --- Exit logic (checked first — exits take priority over new entries) ---
        if has_position:
            if row["ema_cross"] == -1.0:
                return Signal.SELL

        # --- Entry logic ---
        cross_up = row["ema_cross"] == 1.0
        vol_ok = row["vol_ratio"] >= self.config["volume_confirmation_ratio"]
        rsi_ok = self.config["rsi_oversold"] < row["rsi"] < self.config["rsi_overbought"]
        trend_ok = row["close"] > row["ema_slow"]

        signal = Signal.HOLD
        if not has_position and cross_up and vol_ok and rsi_ok and trend_ok:
            signal = Signal.BUY

        # Return reasons alongside signal so the caller can log with the symbol name
        if not has_position:
            reasons = []
            if not cross_up:   reasons.append("no EMA crossover")
            if not vol_ok:     reasons.append("volume too low")
            if not rsi_ok:     reasons.append("RSI out of range")
            if not trend_ok:   reasons.append("price below slow EMA")
            self._last_reason = ", ".join(reasons) if reasons else "conditions met"
        else:
            self._last_reason = "holding position"

        return signal

    # ------------------------------------------------------------------
    # Vectorised versions — used by BacktestEngine to stay in sync
    # ------------------------------------------------------------------

    def entry_mask(self, df: pd.DataFrame) -> pd.Series:
        """Boolean Series: True on bars that should trigger a BUY."""
        cross_up = df["ema_cross"] == 1.0
        vol_ok = df["vol_ratio"] >= self.config["volume_confirmation_ratio"]
        rsi_ok = (df["rsi"] > self.config["rsi_oversold"]) & (df["rsi"] < self.config["rsi_overbought"])
        trend_ok = df["close"] > df["ema_slow"]
        return cross_up & vol_ok & rsi_ok & trend_ok

    def exit_mask(self, df: pd.DataFrame) -> pd.Series:
        """Boolean Series: True on bars that should trigger a SELL."""
        return df["ema_cross"] == -1.0
