@echo off
rem Carrefour prices from this Windows PC (normal connection). Double-click for the test, or:  run_carrefour_windows.cmd full
rem First time: Python 3.10+ (python.org, tick "Add to PATH") and Git are needed. The script gets the code by itself.
setlocal
set "MODE=%~1"
if "%MODE%"=="" set "MODE=test"
set "BASE=%USERPROFILE%\Desktop\cpi"
set "REPO=%BASE%\repo"
set "BRANCH=claude/sleepy-lamport-dwu4iw"
if not exist "%BASE%" mkdir "%BASE%"
python --version || (echo Python 3.10+ is needed: https://www.python.org/downloads/ & pause & exit /b 1)
git --version || (echo Git is needed: https://git-scm.com/download/win & pause & exit /b 1)
if not exist "%REPO%\.git" git clone --branch %BRANCH% https://github.com/waleedhuniti/CPI-Web-Scarping.git "%REPO%" || goto :err
cd /d "%REPO%"
git pull origin %BRANCH% || goto :err
python -m pip install --quiet --upgrade "scrapling[fetchers]" openpyxl || goto :err
echo.
if /i "%MODE%"=="full" (python scripts\pc\carrefour_pc.py) else (python scripts\pc\carrefour_pc.py --test)
echo.
echo Done. Send the .zip file named above (folder %REPO%\data\runs) and the lines printed above.
pause
exit /b 0
:err
echo Setup failed - see the messages above.
pause
exit /b 1
