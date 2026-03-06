from __future__ import annotations

import math


class RiskManager:
    """
    Handles position sizing and trading halts.

    Position sizing uses percentage-of-portfolio allocation, which is appropriate
    for small accounts (< $1,000) where ATR-based risk sizing would produce
    sub-dollar positions that Alpaca cannot fill.
    """

    def __init__(self, config: dict):
        self.config = config

    def compute_position_size(
        self,
        portfolio_value: float,
        entry_price: float,
    ) -> tuple[int, float]:
        """
        Returns (whole_shares, fractional_dollar_amount).

        Alpaca supports two order modes:
          - qty: whole shares (standard)
          - notional: dollar amount (for fractional shares)

        When whole_shares == 0 and fractional_dollar_amount > 0, the caller
        should use a notional order instead.
        """
        position_value = portfolio_value * self.config["position_pct_of_portfolio"]

        if entry_price <= 0:
            return 0, 0.0

        whole_shares = math.floor(position_value / entry_price)
        fractional_dollars = round(position_value, 2)

        return whole_shares, fractional_dollars

    def compute_stop_price(self, entry_price: float, atr: float) -> float:
        """Hard stop price = entry - (ATR * multiplier)."""
        stop = entry_price - atr * self.config.get("atr_stop_multiplier", 2.0)
        return round(max(stop, 0.01), 2)

    def is_daily_loss_limit_breached(self, daily_pnl_pct: float) -> bool:
        """Returns True if daily P&L has fallen below the configured threshold."""
        return daily_pnl_pct <= -abs(self.config["daily_loss_limit"])

    def max_positions_reached(self, open_position_count: int) -> bool:
        return open_position_count >= self.config["max_open_positions"]
