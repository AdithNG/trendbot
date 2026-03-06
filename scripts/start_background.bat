@echo off
echo Starting TrendBot in background...
echo Logs will be written to: logs\trading_bot.log
echo To stop the bot, open Task Manager and end "python.exe"
echo.
start /b pythonw -u scripts\run_paper.py
echo Bot launched. You can close this window.
pause
