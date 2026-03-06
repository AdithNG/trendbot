import pandas as pd
import pytest
from src.signals.indicators import compute_indicators


def test_indicator_columns_present(sample_ohlcv, strategy_config):
    df = compute_indicators(sample_ohlcv, strategy_config)
    expected = {"ema_fast", "ema_slow", "atr", "rsi", "vol_ratio", "ema_cross"}
    assert expected.issubset(set(df.columns))


def test_no_nulls_at_tail(sample_ohlcv, strategy_config):
    df = compute_indicators(sample_ohlcv, strategy_config)
    tail = df.iloc[-10:]
    nulls = tail[["ema_fast", "ema_slow", "atr", "rsi"]].isna().sum().sum()
    assert nulls == 0, f"Unexpected nulls in last 10 rows: {nulls}"


def test_ema_fast_above_slow_during_uptrend(sample_ohlcv, strategy_config):
    df = compute_indicators(sample_ohlcv, strategy_config)
    # Around bar 80-100 we should be in an uptrend so fast EMA > slow EMA
    mid = df.iloc[80:100]
    assert (mid["ema_fast"] > mid["ema_slow"]).any()


def test_ema_cross_values(sample_ohlcv, strategy_config):
    df = compute_indicators(sample_ohlcv, strategy_config)
    valid_values = {-1.0, 0.0, 1.0}
    unique = set(df["ema_cross"].unique())
    assert unique.issubset(valid_values), f"Unexpected ema_cross values: {unique}"


def test_vol_ratio_positive(sample_ohlcv, strategy_config):
    df = compute_indicators(sample_ohlcv, strategy_config).dropna()
    assert (df["vol_ratio"] > 0).all()
