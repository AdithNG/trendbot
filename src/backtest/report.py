from __future__ import annotations

import os
import vectorbt as vbt


class BacktestReport:
    def print_summary(self, metrics: dict, label: str = "BACKTEST RESULTS"):
        print("\n" + "=" * 60)
        print(label)
        print("=" * 60)
        print(f"  Total Return:        {metrics['total_return_pct']:>8.2f}%")
        print(f"  Annualized Return:   {metrics['annualized_return_pct']:>8.2f}%")
        print(f"  Sharpe Ratio:        {metrics['sharpe_ratio']:>8.3f}")
        print(f"  Sortino Ratio:       {metrics['sortino_ratio']:>8.3f}")
        print(f"  Max Drawdown:        {metrics['max_drawdown_pct']:>8.2f}%")
        print(f"  Win Rate:            {metrics['win_rate_pct']:>8.2f}%")
        print(f"  Total Trades:        {metrics['total_trades']:>8}")
        print(f"  Profit Factor:       {metrics['profit_factor']:>8.2f}")
        print("=" * 60 + "\n")

    def save_html(self, portfolio: vbt.Portfolio, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        portfolio.plot().write_html(path)
        print(f"Chart saved to: {path}")
