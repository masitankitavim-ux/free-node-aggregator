@echo off
REM ============================================================
REM  Free Node Aggregator - LOCAL run (China vantage)
REM
REM  Why: GitHub Actions runs on an overseas runner, so it can
REM  only tell you "the node is alive somewhere". This script
REM  runs the SAME real mihomo test on YOUR machine, so the nodes
REM  you get are the ones that actually work from here.
REM
REM  Usage:  double-click, or  run_local.bat  from a terminal
REM ============================================================
setlocal
cd /d "%~dp0"

set PY=python
if exist ".venv\Scripts\python.exe" set PY=.venv\Scripts\python.exe

set MIHOMO=
if exist "%~dp0mihomo.exe" set MIHOMO=%~dp0mihomo.exe
if not defined MIHOMO (
  for %%I in (mihomo.exe) do if not "%%~$PATH:I"=="" set MIHOMO=%%~$PATH:I
)
if not defined MIHOMO (
  echo [*] mihomo.exe not found, trying to download ...
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0get_mihomo.ps1"
  if exist "%~dp0mihomo.exe" set MIHOMO=%~dp0mihomo.exe
)

echo.
if defined MIHOMO (
  echo [*] mihomo : %MIHOMO%
  echo [*] testing nodes from THIS machine ^(real connectivity^) ...
  %PY% aggregator.py --config config.yaml --out output --mihomo "%MIHOMO%"
) else (
  echo [!] no mihomo - falling back to TCP ping. RESULTS WILL BE UNRELIABLE.
  %PY% aggregator.py --config config.yaml --out output
)
set RC=%ERRORLEVEL%

echo.
if %RC%==0 (
  echo [OK] done. subscriptions are in %~dp0output
) else (
  echo [!] aggregator exited with code %RC% - check the log above.
)
echo.
echo [i] to publish these results:
echo       git add output ^&^& git commit -m "chore: update free nodes" ^&^& git push
endlocal