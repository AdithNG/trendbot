from __future__ import annotations

import time
from datetime import datetime, time as dt_time

import pytz
import schedule
from loguru import logger

from src.data.fetcher import DataFetcher
from src.data.universe import UniverseSelector
from src.signals.indicators import compute_indicators
from src.signals.generator import Signal, SignalGenerator
from src.strategy.risk import RiskManager
from src.broker.alpaca_client import AlpacaClient
from src.bot.state import PortfolioState

EASTERN = pytz.timezone("US/Eastern")


class BotRunner:
    """
    Main trading loop.

    On each scheduled cycle:
      1. Check if market is open and within trading window
      2. Check daily loss limit
      3. Fetch warmup bars for all universe symbols
      4. Compute indicators and generate signals
      5. Execute BUY / SELL orders via AlpacaClient
    """

    def __init__(self, config: dict, broker: AlpacaClient):
        self.config = config
        self.broker = broker
        self.fetcher = DataFetcher()
        self.universe = UniverseSelector(config)
        self.sg = SignalGenerator(config["strategy"])
        self.rm = RiskManager(config["risk"])
        self.state = PortfolioState()
        self._entries_today: set[str] = set()  # symbols bought today (PDT tracking)
        self._entries_date: str = ""

    # ------------------------------------------------------------------
    # Market hours guard
    # ------------------------------------------------------------------

    def _in_trading_window(self) -> bool:
        now = datetime.now(EASTERN)
        if now.weekday() >= 5:  # Weekend
            return False

        open_buffer = self.config["schedule"]["market_open_buffer_minutes"]
        close_buffer = self.config["schedule"]["market_close_buffer_minutes"]

        open_minutes = 9 * 60 + 30 + open_buffer
        close_minutes = 16 * 60 - close_buffer

        now_minutes = now.hour * 60 + now.minute
        return open_minutes <= now_minutes <= close_minutes

    # ------------------------------------------------------------------
    # Core cycle
    # ------------------------------------------------------------------

    def run_cycle(self):
        if not self._in_trading_window():
            logger.debug("Outside trading window - skipping cycle")
            return

        if not self.broker.is_market_open():
            logger.debug("Market not open according to Alpaca clock - skipping")
            return

        account = self.broker.get_account()
        portfolio_value = account["portfolio_value"]
        daytrade_count = account["daytrade_count"]
        self.state.update_equity(portfolio_value)

        # Reset today's entry set at the start of each new trading day
        today = datetime.now(EASTERN).date().isoformat()
        if self._entries_date != today:
            self._entries_today = set()
            self._entries_date = today

        if self.rm.is_daily_loss_limit_breached(self.state.daily_pnl_pct):
            logger.warning(
                f"Daily loss limit breached ({self.state.daily_pnl_pct:.2%}). "
                "No new trades today."
            )
            return

        symbols = self.universe.get_universe()
        price_data = self.fetcher.get_warmup_bars(symbols, lookback_days=120)
        open_positions = self.broker.get_open_positions()

        for symbol, df in price_data.items():
            try:
                df = compute_indicators(df, self.config["strategy"])
                has_position = symbol in open_positions

                signal = self.sg.get_signal(df, has_position)

                if signal == Signal.BUY:
                    if self.rm.max_positions_reached(len(open_positions)):
                        continue

                    entry_price = df["close"].iloc[-1]
                    atr = df["atr"].iloc[-1]
                    whole_shares, notional = self.rm.compute_position_size(
                        portfolio_value, entry_price
                    )
                    stop = self.rm.compute_stop_price(entry_price, atr)

                    if whole_shares > 0:
                        self.broker.place_market_order_qty(symbol, whole_shares, "BUY")
                        self.state.record_entry(symbol, entry_price, whole_shares, stop)
                        self._entries_today.add(symbol)
                        open_positions[symbol] = {}  # Prevent duplicate orders this cycle
                    elif notional >= 1.0:  # Fractional order minimum $1
                        self.broker.place_market_order_notional(symbol, notional, "BUY")
                        self.state.record_entry(symbol, entry_price, notional / entry_price, stop)
                        self._entries_today.add(symbol)
                        open_positions[symbol] = {}

                elif signal == Signal.SELL and has_position:
                    if self.rm.pdt_sell_blocked(symbol, portfolio_value, self._entries_today, daytrade_count):
                        logger.warning(
                            f"PDT: skipping sell of {symbol} - bought today and day trade limit nearly reached. "
                            "Will hold overnight."
                        )
                        continue
                    self.broker.close_position(symbol)
                    self.state.record_exit(symbol)
                    open_positions.pop(symbol, None)

            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")

    # ------------------------------------------------------------------
    # Crypto cycle (24/7, no market hours, no PDT)
    # ------------------------------------------------------------------

    def run_crypto_cycle(self):
        """
        Crypto trading cycle.

        Differences from equity cycle:
          - Runs 24/7 (no market hours guard)
          - No PDT restriction (crypto is exempt)
          - Always uses notional orders (BTC prices make whole-share qty impractical)
        """
        account = self.broker.get_account()
        portfolio_value = account["portfolio_value"]
        self.state.update_equity(portfolio_value)

        if self.rm.is_daily_loss_limit_breached(self.state.daily_pnl_pct):
            logger.warning(
                f"Daily loss limit breached ({self.state.daily_pnl_pct:.2%}). "
                "No new crypto trades."
            )
            return

        symbols = self.universe.get_crypto_universe()
        if not symbols:
            return

        price_data = self.fetcher.get_crypto_warmup_bars(symbols, lookback_days=120)
        open_positions = self.broker.get_open_positions()

        for symbol, df in price_data.items():
            try:
                df = compute_indicators(df, self.config["strategy"])
                has_position = symbol in open_positions

                signal = self.sg.get_signal(df, has_position)

                if signal == Signal.BUY:
                    if self.rm.max_positions_reached(len(open_positions)):
                        continue

                    entry_price = df["close"].iloc[-1]
                    atr = df["atr"].iloc[-1]
                    _, notional = self.rm.compute_position_size(portfolio_value, entry_price)
                    stop = self.rm.compute_stop_price(entry_price, atr)

                    if notional >= 1.0:
                        self.broker.place_market_order_notional(symbol, notional, "BUY")
                        self.state.record_entry(symbol, entry_price, notional / entry_price, stop)
                        open_positions[symbol] = {}
                        logger.info(f"Crypto BUY: ${notional:.2f} of {symbol} @ {entry_price:.2f}")

                elif signal == Signal.SELL and has_position:
                    # No PDT check for crypto
                    self.broker.close_position(symbol)
                    self.state.record_exit(symbol)
                    open_positions.pop(symbol, None)

            except Exception as e:
                logger.error(f"Error processing crypto {symbol}: {e}")

    # ------------------------------------------------------------------
    # Trailing stop check (runs every cycle for open positions)
    # ------------------------------------------------------------------

    def check_trailing_stops(self):
        open_positions = self.broker.get_open_positions()
        trailing_activation = self.config["risk"].get("trailing_stop_activation", 0.05)
        atr_trail_mult = self.config["strategy"].get("atr_stop_multiplier", 2.0) * 0.75

        for symbol, pos_info in open_positions.items():
            state_pos = self.state.get_position(symbol)
            if not state_pos:
                continue

            current_price = pos_info["current_price"]
            self.state.update_high(symbol, current_price)

            gain_pct = (current_price - state_pos.entry_price) / state_pos.entry_price
            if gain_pct >= trailing_activation:
                # Fetch latest ATR to set trail
                data = self.fetcher.get_warmup_bars([symbol], lookback_days=30)
                if symbol in data:
                    df = compute_indicators(data[symbol], self.config["strategy"])
                    atr = df["atr"].iloc[-1]
                    trail_stop = state_pos.high_since_entry - atr * atr_trail_mult
                    if current_price < trail_stop:
                        logger.info(f"Trailing stop hit for {symbol} at {current_price:.2f}")
                        self.broker.close_position(symbol)
                        self.state.record_exit(symbol)

    # ------------------------------------------------------------------
    # Start
    # ------------------------------------------------------------------

    def start(self):
        interval = self.config["schedule"]["data_refresh_interval_minutes"]
        schedule.every(interval).minutes.do(self.run_cycle)
        schedule.every(interval).minutes.do(self.check_trailing_stops)
        schedule.every(interval).minutes.do(self.run_crypto_cycle)
        logger.info(f"Bot started. Equity + crypto scanning every {interval} minutes.")
        self.run_cycle()
        self.check_trailing_stops()
        self.run_crypto_cycle()
        while True:
            schedule.run_pending()
            time.sleep(30)
