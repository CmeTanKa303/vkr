@echo off
setlocal
cd /d "%~dp0backend"

if exist "nextburger.db" (
  del /f /q "nextburger.db"
  echo Database removed. It will be recreated with the initial catalog
  echo and the admin account on the next launch.
) else (
  echo No database file found - nothing to reset.
)
echo.
pause
