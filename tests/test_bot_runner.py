"""
Integration-style tests for BotRunner using MockBroker.
No Alpaca keys required.
"""
from __future__ import annotations

import pandas as pd
import pytest

from src.bot.runner import BotRunner
from src.bot.state import PortfolioState
from src.broker.mock_client import MockBroker


@pytest.fixture
def full_config(strategy_config, risk_config):
    return {
        "strategy": strategy_config,
        "risk": risk_config,
        "universe": {
            "mode": "sp500_top_liquid",
            "max_symbols": 5,
            "min_avg_volume": 5_000_000,
        },
        "schedule": {
            "data_refresh_interval_minutes": 5,
            "market_open_buffer_minutes": 0,
            "market_close_buffer_minutes": 0,
        },
        "logging": {"level": "WARNING", "log_dir": "logs/"},
    }


def test_mock_broker_account(full_config):
    broker = MockBroker(initial_cash=10_000)
    account = broker.get_account()
    assert account["cash"] == 10_000
    assert account["portfolio_value"] == 10_000


def test_mock_broker_buy_and_close(full_config):
    broker = MockBroker(initial_cash=10_000)

    broker.place_market_order_qty("AAPL", 5, "BUY")
    broker.set_price("AAPL", 200.0)  # set a price so we can track position
    positions = broker.get_open_positions()
    assert "AAPL" in positions
    assert positions["AAPL"]["qty"] == 5

    broker.close_position("AAPL")
    assert "AAPL" not in broker.get_open_positions()


def test_mock_broker_market_closed(full_config):
    broker = MockBroker(market_open=False)
    assert not broker.is_market_open()


def test_portfolio_state_daily_pnl(full_config):
    state = PortfolioState()
    state.update_equity(10_000)
    state.update_equity(9_500)
    assert state.daily_pnl_pct == pytest.approx(-0.05, abs=0.001)


def test_portfolio_state_resets_on_new_day(full_config):
    from datetime import date, timedelta
    from unittest.mock import patch

    state = PortfolioState()

    today = date.today()
    tomorrow = today + timedelta(days=1)

    with patch("src.bot.state.date") as mock_date:
        mock_date.today.return_value = today
        state.update_equity(10_000)

    with patch("src.bot.state.date") as mock_date:
        mock_date.today.return_value = tomorrow
        state.update_equity(10_500)
        # New day: day_start_equity resets to 10_500 so pnl == 0
        assert state.daily_pnl_pct == pytest.approx(0.0, abs=0.001)
