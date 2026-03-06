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

    def pdt_sell_blocked(
        self,
        symbol: str,
        portfolio_value: float,
        entries_today: set[str],
        daytrade_count: int,
    ) -> bool:
        """
        Returns True if selling `symbol` would constitute an illegal day trade.

        PDT rule: accounts under $25,000 are limited to 3 day trades per
        rolling 5-business-day window.  A day trade = buy and sell the same
        symbol on the same calendar day.

        We block the sell (hold overnight instead) when ALL of these are true:
          - Portfolio < $25,000
          - The symbol was bought today (would be a day trade)
          - We've already used 2 of our 3 allowed day trades this week
        """
        PDT_THRESHOLD = 25_000
        PDT_MAX = self.config.get("pdt_max_day_trades", 3)

        if portfolio_value >= PDT_THRESHOLD:
            return False  # PDT rule doesn't apply

        if symbol not in entries_today:
            return False  # Overnight position — selling is fine

        remaining = PDT_MAX - daytrade_count
        if remaining > 1:
            return False  # Still have day trades to spare

        return True  # Would burn last day trade — hold overnight
