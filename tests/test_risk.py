import pytest
from src.strategy.risk import RiskManager


def test_position_size_whole_shares(risk_config):
    rm = RiskManager(risk_config)
    # $1000 portfolio, 25% = $250 per position, stock at $50 → 5 shares
    whole, notional = rm.compute_position_size(portfolio_value=1000.0, entry_price=50.0)
    assert whole == 5
    assert notional == pytest.approx(250.0, abs=0.01)


def test_position_size_fractional_for_small_account(risk_config):
    rm = RiskManager(risk_config)
    # $50 portfolio, 25% = $12.50, stock at $100 → 0 whole shares, use notional
    whole, notional = rm.compute_position_size(portfolio_value=50.0, entry_price=100.0)
    assert whole == 0
    assert notional == pytest.approx(12.50, abs=0.01)


def test_position_size_zero_price(risk_config):
    rm = RiskManager(risk_config)
    whole, notional = rm.compute_position_size(portfolio_value=1000.0, entry_price=0.0)
    assert whole == 0
    assert notional == 0.0


def test_stop_price_below_entry(risk_config):
    rm = RiskManager(risk_config)
    stop = rm.compute_stop_price(entry_price=100.0, atr=5.0)
    # stop = 100 - (5 * 2.0) = 90.0
    assert stop == pytest.approx(90.0, abs=0.01)


def test_daily_loss_limit_not_breached(risk_config):
    rm = RiskManager(risk_config)
    assert not rm.is_daily_loss_limit_breached(-0.02)  # -2% is fine


def test_daily_loss_limit_breached(risk_config):
    rm = RiskManager(risk_config)
    assert rm.is_daily_loss_limit_breached(-0.06)  # -6% triggers halt


def test_max_positions_not_reached(risk_config):
    rm = RiskManager(risk_config)
    assert not rm.max_positions_reached(3)  # 3 < 4


def test_max_positions_reached(risk_config):
    rm = RiskManager(risk_config)
    assert rm.max_positions_reached(4)  # 4 >= 4
