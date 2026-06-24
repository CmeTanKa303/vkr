@echo off
setlocal
cd /d "%~dp0backend"

echo ============================================
echo    Next Burger - local server
echo ============================================
echo.

if not exist ".venv\Scripts\python.exe" goto setup
echo [OK] Virtual environment found.
goto run

:setup
echo [1/3] Creating Python virtual environment...
python -m venv .venv
if errorlevel 1 goto nopython
echo [2/3] Installing dependencies (first run, may take a couple of minutes)...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto pipfail
goto run

:run
echo.
echo [3/3] Server:   http://localhost:8000
echo        Admin:    http://localhost:8000/admin
echo        API docs: http://localhost:8000/docs
echo.
echo Opening the site in your browser in a few seconds...
echo To STOP the server press Ctrl+C in this window.
echo.
start "" cmd /c "timeout /t 4 >nul & start http://localhost:8000"
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
echo.
echo Server stopped.
pause
goto :eof

:nopython
echo.
echo ERROR: Python was not found.
echo Install Python 3.10+ from https://www.python.org/downloads/
echo and tick "Add Python to PATH" during installation, then run this file again.
echo.
pause
goto :eof

:pipfail
echo.
echo ERROR while installing dependencies. Check your internet connection and try again.
echo.
pause
goto :eof
