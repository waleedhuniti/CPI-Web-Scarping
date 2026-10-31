@echo off
rem Emirates fares for the tickets sheet (out 6 Nov, back 13 Nov 2026) on a Windows PC with a normal home or office connection.
rem Double-click, or run from a terminal. Extra arguments are airport codes, e.g.  run_ek_windows.cmd RUH IST
cd /d "%~dp0"
python --version || (echo Python 3.10+ is needed: https://www.python.org/downloads/ & pause & exit /b 1)
python -m pip install --quiet --upgrade "scrapling[fetchers]" openpyxl || goto :err
scrapling install || goto :err
python ek_fares.py 2026-11-06 2026-11-13 runs_6_13\ek_res.json %*
echo.
echo Done. Results: runs_6_13\ek_res.json   Screenshots: ek_debug\
pause
exit /b 0
:err
echo Setup failed - see the messages above.
pause
exit /b 1
