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

        # Log what the indicators look like and why the signal is what it is
        reasons = []
        if not cross_up:
            reasons.append(f"no_cross(ema_fast={row['ema_fast']:.2f} vs ema_slow={row['ema_slow']:.2f})")
        if not vol_ok:
            reasons.append(f"vol_low({row['vol_ratio']:.2f}x < {self.config['volume_confirmation_ratio']}x)")
        if not rsi_ok:
            reasons.append(f"rsi_out({row['rsi']:.1f}, need {self.config['rsi_oversold']}-{self.config['rsi_overbought']})")
        if not trend_ok:
            reasons.append(f"below_ema(close={row['close']:.2f} < ema_slow={row['ema_slow']:.2f})")

        hold_reason = ", ".join(reasons) if reasons else "all_ok"
        logger.debug(
            f"Signal={signal.value} pos={has_position} | "
            f"rsi={row['rsi']:.1f} vol={row['vol_ratio']:.2f}x "
            f"ema_fast={row['ema_fast']:.2f} ema_slow={row['ema_slow']:.2f} "
            f"cross={int(row['ema_cross'])} | {hold_reason}"
        )

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
