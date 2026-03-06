from __future__ import annotations

import pandas as pd
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange


def compute_indicators(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    Adds indicator columns to a single symbol's OHLCV DataFrame.

    Input columns required: open, high, low, close, volume
    Added columns:
      ema_fast      - Fast EMA (default 20)
      ema_slow      - Slow EMA (default 50)
      atr           - Average True Range
      rsi           - RSI
      vol_avg_20    - 20-bar rolling average volume
      vol_ratio     - current volume / vol_avg_20
      ema_above     - 1 if ema_fast > ema_slow, else 0
      ema_cross     - 1.0 on cross up, -1.0 on cross down, 0 otherwise
    """
    df = df.copy()

    df["ema_fast"] = EMAIndicator(
        close=df["close"], window=config["fast_ema"], fillna=False
    ).ema_indicator()

    df["ema_slow"] = EMAIndicator(
        close=df["close"], window=config["slow_ema"], fillna=False
    ).ema_indicator()

    df["atr"] = AverageTrueRange(
        high=df["high"],
        low=df["low"],
        close=df["close"],
        window=config["atr_period"],
        fillna=False,
    ).average_true_range()

    df["rsi"] = RSIIndicator(
        close=df["close"], window=config["rsi_period"], fillna=False
    ).rsi()

    df["vol_avg_20"] = df["volume"].rolling(20).mean()
    df["vol_ratio"] = df["volume"] / df["vol_avg_20"]

    # EMA crossover: +1 on cross up, -1 on cross down, 0 otherwise
    df["ema_above"] = (df["ema_fast"] > df["ema_slow"]).astype(int)
    df["ema_cross"] = df["ema_above"].diff().fillna(0)

    return df
