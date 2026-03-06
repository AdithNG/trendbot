from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class PositionRecord:
    symbol: str
    entry_price: float
    qty: float
    stop_price: float
    high_since_entry: float = 0.0


class PortfolioState:
    """
    Tracks open positions, daily P&L, and stop levels in memory.

    This is the bot's internal view of what it owns.  Alpaca is always
    the source of truth for actual fills and account value — this state
    is used for signal filtering and stop-loss monitoring only.
    """

    def __init__(self):
        self._positions: dict[str, PositionRecord] = {}
        self._day_start_equity: float | None = None
        self._current_equity: float = 0.0
        self._current_date: date | None = None

    # ------------------------------------------------------------------
    # Position management
    # ------------------------------------------------------------------

    def record_entry(self, symbol: str, price: float, qty: float, stop: float):
        self._positions[symbol] = PositionRecord(
            symbol=symbol,
            entry_price=price,
            qty=qty,
            stop_price=stop,
            high_since_entry=price,
        )

    def record_exit(self, symbol: str):
        self._positions.pop(symbol, None)

    def has_position(self, symbol: str) -> bool:
        return symbol in self._positions

    def get_position(self, symbol: str) -> PositionRecord | None:
        return self._positions.get(symbol)

    def update_high(self, symbol: str, current_price: float):
        pos = self._positions.get(symbol)
        if pos and current_price > pos.high_since_entry:
            pos.high_since_entry = current_price

    @property
    def open_position_count(self) -> int:
        return len(self._positions)

    # ------------------------------------------------------------------
    # Daily P&L tracking
    # ------------------------------------------------------------------

    def update_equity(self, equity: float):
        today = date.today()
        if self._current_date != today:
            self._day_start_equity = equity
            self._current_date = today
        self._current_equity = equity

    @property
    def daily_pnl_pct(self) -> float:
        if not self._day_start_equity:
            return 0.0
        return (self._current_equity - self._day_start_equity) / self._day_start_equity
