import numpy as np
import pandas as pd
import pytest
from src.signals.indicators import compute_indicators
from src.signals.generator import Signal, SignalGenerator


def _inject_cross_up(df: pd.DataFrame):
    """Force a cross-up on the last bar for deterministic BUY signal testing."""
    df = df.copy()
    df.loc[df.index[-1], "ema_cross"] = 1.0
    df.loc[df.index[-1], "ema_fast"] = df.loc[df.index[-1], "ema_slow"] + 1.0
    df.loc[df.index[-1], "close"] = df.loc[df.index[-1], "ema_slow"] + 1.0
    df.loc[df.index[-1], "rsi"] = 50.0
    df.loc[df.index[-1], "vol_ratio"] = 2.0
    return df


def _inject_cross_down(df: pd.DataFrame):
    """Force a cross-down on the last bar for deterministic SELL signal testing."""
    df = df.copy()
    df.loc[df.index[-1], "ema_cross"] = -1.0
    return df


def test_buy_signal_on_cross_up(sample_ohlcv, strategy_config):
    df = compute_indicators(sample_ohlcv, strategy_config).dropna()
    df = _inject_cross_up(df)
    sg = SignalGenerator(strategy_config)
    assert sg.get_signal(df, has_position=False) == Signal.BUY


def test_no_buy_when_already_in_position(sample_ohlcv, strategy_config):
    df = compute_indicators(sample_ohlcv, strategy_config).dropna()
    df = _inject_cross_up(df)
    sg = SignalGenerator(strategy_config)
    assert sg.get_signal(df, has_position=True) != Signal.BUY


def test_sell_signal_on_cross_down(sample_ohlcv, strategy_config):
    df = compute_indicators(sample_ohlcv, strategy_config).dropna()
    df = _inject_cross_down(df)
    sg = SignalGenerator(strategy_config)
    assert sg.get_signal(df, has_position=True) == Signal.SELL


def test_hold_when_no_cross(sample_ohlcv, strategy_config):
    df = compute_indicators(sample_ohlcv, strategy_config).dropna()
    df.loc[df.index[-1], "ema_cross"] = 0.0
    sg = SignalGenerator(strategy_config)
    # HOLD when not in position and no cross
    assert sg.get_signal(df, has_position=False) == Signal.HOLD


def test_entry_mask_is_boolean_series(sample_ohlcv, strategy_config):
    df = compute_indicators(sample_ohlcv, strategy_config).dropna()
    sg = SignalGenerator(strategy_config)
    mask = sg.entry_mask(df)
    assert mask.dtype == bool
    assert len(mask) == len(df)


def test_exit_mask_is_boolean_series(sample_ohlcv, strategy_config):
    df = compute_indicators(sample_ohlcv, strategy_config).dropna()
    sg = SignalGenerator(strategy_config)
    mask = sg.exit_mask(df)
    assert mask.dtype == bool
