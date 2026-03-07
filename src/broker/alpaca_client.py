from __future__ import annotations

import os
from loguru import logger

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, ClosePositionRequest
from alpaca.trading.enums import OrderSide, TimeInForce


class AlpacaClient:
    """
    Thin wrapper over alpaca-py TradingClient.

    All broker interaction goes through this class — it is the single mock point
    for testing and the boundary between simulation and real capital.

    paper=True  → uses paper-api.alpaca.markets (safe, fake money)
    paper=False → uses api.alpaca.markets (REAL MONEY — handle with care)
    """

    def __init__(self, api_key: str, secret_key: str, paper: bool = True):
        self.paper = paper
        self.client = TradingClient(
            api_key=api_key,
            secret_key=secret_key,
            paper=paper,
        )
        mode = "PAPER" if paper else "LIVE"
        logger.info(f"AlpacaClient initialised in {mode} mode")

    # ------------------------------------------------------------------
    # Account
    # ------------------------------------------------------------------

    def get_account(self) -> dict:
        acct = self.client.get_account()
        return {
            "portfolio_value": float(acct.portfolio_value),
            "cash": float(acct.cash),
            "buying_power": float(acct.buying_power),
            "equity": float(acct.equity),
            "daytrade_count": int(acct.daytrade_count),
        }

    # ------------------------------------------------------------------
    # Positions
    # ------------------------------------------------------------------

    def get_open_positions(self) -> dict[str, dict]:
        """Returns {symbol: position_info} for all currently open positions."""
        positions = self.client.get_all_positions()
        return {
            p.symbol: {
                "qty": float(p.qty),
                "avg_entry_price": float(p.avg_entry_price),
                "current_price": float(p.current_price),
                "unrealized_pl": float(p.unrealized_pl),
                "unrealized_plpc": float(p.unrealized_plpc),
            }
            for p in positions
        }

    def close_position(self, symbol: str):
        """Market-sells the entire position in `symbol`."""
        self.client.close_position(symbol)
        logger.info(f"Closed position: {symbol}")

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------

    @staticmethod
    def _tif(symbol: str) -> TimeInForce:
        """Crypto requires GTC; equities use DAY."""
        return TimeInForce.GTC if "/" in symbol else TimeInForce.DAY

    def place_market_order_qty(self, symbol: str, qty: float, side: str) -> str:
        """Place a market order for a whole number of shares."""
        order_side = OrderSide.BUY if side.upper() == "BUY" else OrderSide.SELL
        req = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=order_side,
            time_in_force=self._tif(symbol),
        )
        order = self.client.submit_order(req)
        logger.info(f"Order placed: {side} {qty} of {symbol} | id={order.id}")
        return str(order.id)

    def place_market_order_notional(self, symbol: str, notional: float, side: str) -> str:
        """
        Place a fractional market order using a dollar amount.
        Used for small accounts where floor(position_value / price) == 0.
        Also the preferred method for crypto (arbitrary fractional quantities).
        """
        order_side = OrderSide.BUY if side.upper() == "BUY" else OrderSide.SELL
        req = MarketOrderRequest(
            symbol=symbol,
            notional=round(notional, 2),
            side=order_side,
            time_in_force=self._tif(symbol),
        )
        order = self.client.submit_order(req)
        logger.info(f"Order placed: {side} ${notional:.2f} of {symbol} (notional) | id={order.id}")
        return str(order.id)

    def is_market_open(self) -> bool:
        clock = self.client.get_clock()
        return clock.is_open
