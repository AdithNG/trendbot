"""
Shared pytest fixtures.
"""

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def sample_ohlcv():
    """
    200 bars of synthetic daily OHLCV data with a visible uptrend then downtrend.
    Provides enough history for EMA(50) and RSI(14) to warm up.
    """
    rng = np.random.default_rng(seed=42)
    n = 200
    # RangeIndex avoids a pandas 2.2.x + numpy 1.26.x DatetimeIndex crash on Windows.
    # Indicators only care about ordering, not actual dates.
    dates = pd.RangeIndex(n)

    close = 100.0
    closes = []
    for i in range(n):
        # Uptrend for first 120 bars, downtrend for next 80
        drift = 0.3 if i < 120 else -0.4
        close *= 1 + drift / 100 + rng.normal(0, 0.01)
        closes.append(close)

    closes = np.array(closes)
    opens = closes * (1 + rng.normal(0, 0.003, n))
    highs = np.maximum(opens, closes) * (1 + rng.uniform(0, 0.005, n))
    lows = np.minimum(opens, closes) * (1 - rng.uniform(0, 0.005, n))
    volumes = rng.integers(1_000_000, 5_000_000, n).astype(float)

    return pd.DataFrame(
        {"open": opens, "high": highs, "low": lows, "close": closes, "volume": volumes},
        index=dates,
    )


@pytest.fixture
def strategy_config():
    return {
        "fast_ema": 20,
        "slow_ema": 50,
        "atr_period": 14,
        "atr_stop_multiplier": 2.0,
        "volume_confirmation_ratio": 1.5,
        "rsi_period": 14,
        "rsi_overbought": 65,
        "rsi_oversold": 35,
    }


@pytest.fixture
def risk_config():
    return {
        "position_pct_of_portfolio": 0.25,
        "max_open_positions": 4,
        "daily_loss_limit": 0.05,
        "atr_stop_multiplier": 2.0,
    }
