from __future__ import annotations

from loguru import logger


class MockBroker:
    """
    In-memory broker that mimics AlpacaClient for testing and dry-run purposes.

    Orders are never sent to any exchange — fills are assumed instant at the
    price passed in.  Account state is mutated in memory.

    Usage:
        broker = MockBroker(initial_cash=10_000)
        runner = BotRunner(config=config, broker=broker)
        runner.run_cycle()
    """

    def __init__(self, initial_cash: float = 10_000.0, market_open: bool = True):
        self._cash = initial_cash
        self._market_open = market_open
        self._positions: dict[str, dict] = {}
        self._orders: list[dict] = []
        self._order_id = 0

    # ------------------------------------------------------------------
    # Account
    # ------------------------------------------------------------------

    def get_account(self) -> dict:
        equity = self._cash + sum(
            p["qty"] * p["current_price"] for p in self._positions.values()
        )
        return {
            "portfolio_value": equity,
            "cash": self._cash,
            "buying_power": self._cash,
            "equity": equity,
            "daytrade_count": 0,
        }

    # ------------------------------------------------------------------
    # Positions
    # ------------------------------------------------------------------

    def get_open_positions(self) -> dict[str, dict]:
        return dict(self._positions)

    def close_position(self, symbol: str):
        pos = self._positions.pop(symbol, None)
        if pos:
            proceeds = pos["qty"] * pos["current_price"]
            self._cash += proceeds
            logger.info(f"[Mock] Closed {symbol} | proceeds=${proceeds:.2f}")

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------

    def place_market_order_qty(self, symbol: str, qty: float, side: str) -> str:
        self._order_id += 1
        price = self._positions.get(symbol, {}).get("current_price", 100.0)
        self._fill(symbol, qty, price, side)
        order_id = f"mock-{self._order_id}"
        self._orders.append({"id": order_id, "symbol": symbol, "qty": qty, "side": side, "price": price})
        logger.info(f"[Mock] Order {side} {qty} {symbol} @ ${price:.2f} | id={order_id}")
        return order_id

    def place_market_order_notional(self, symbol: str, notional: float, side: str) -> str:
        self._order_id += 1
        price = self._positions.get(symbol, {}).get("current_price", 100.0)
        qty = notional / price if price > 0 else 0
        self._fill(symbol, qty, price, side)
        order_id = f"mock-{self._order_id}"
        self._orders.append({"id": order_id, "symbol": symbol, "notional": notional, "side": side, "price": price})
        logger.info(f"[Mock] Order {side} ${notional:.2f} of {symbol} @ ${price:.2f} | id={order_id}")
        return order_id

    def is_market_open(self) -> bool:
        return self._market_open

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _fill(self, symbol: str, qty: float, price: float, side: str):
        if side.upper() == "BUY":
            cost = qty * price
            self._cash -= cost
            if symbol in self._positions:
                pos = self._positions[symbol]
                total_qty = pos["qty"] + qty
                pos["avg_entry_price"] = (pos["avg_entry_price"] * pos["qty"] + price * qty) / total_qty
                pos["qty"] = total_qty
            else:
                self._positions[symbol] = {
                    "qty": qty,
                    "avg_entry_price": price,
                    "current_price": price,
                    "unrealized_pl": 0.0,
                    "unrealized_plpc": 0.0,
                }
        else:
            self._positions.pop(symbol, None)

    def set_price(self, symbol: str, price: float):
        """Update current price for a held position (for test scenarios)."""
        if symbol in self._positions:
            pos = self._positions[symbol]
            pos["current_price"] = price
            cost_basis = pos["avg_entry_price"] * pos["qty"]
            pos["unrealized_pl"] = price * pos["qty"] - cost_basis
            pos["unrealized_plpc"] = pos["unrealized_pl"] / cost_basis if cost_basis else 0.0

    @property
    def order_history(self) -> list[dict]:
        return list(self._orders)
