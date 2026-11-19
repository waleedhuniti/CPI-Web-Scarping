@echo off
rem Emirates fares for the tickets sheet (out 4 Dec, back 11 Dec 2026) on a Windows PC with a normal home or office connection.
rem Double-click, or run from a terminal. Extra arguments are airport codes, e.g.  run_ek_windows.cmd RUH IST
cd /d "%~dp0"
python --version || (echo Python 3.10+ is needed: https://www.python.org/downloads/ & pause & exit /b 1)
python -m pip install --quiet --upgrade "scrapling[fetchers]" openpyxl || goto :err
scrapling install || goto :err
python ek_fares.py 2026-12-04 2026-12-11 runs_dec_04_11\ek_res.json %*
echo.
echo Done. Results: runs_dec_04_11\ek_res.json   Screenshots: ek_debug\
pause
exit /b 0
:err
echo Setup failed - see the messages above.
pause
exit /b 1
