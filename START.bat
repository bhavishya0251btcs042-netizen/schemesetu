@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title SchemeSetu - AI Citizen Services Navigator (Powered by DAC)

echo ================================================================
echo    SchemeSetu  ^|  AI Citizen Services Navigator
echo    Powered by DAC - DBS Global University R^&D and S^&I Cell
echo ================================================================
echo.

REM --- Check Python ---
python --version >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python was not found on this computer.
  echo.
  echo Please install Python 3.10 or newer from:
  echo    https://www.python.org/downloads/
  echo During install, TICK the box "Add Python to PATH".
  echo.
  pause
  exit /b 1
)

REM --- Create virtual environment on first run ---
if not exist ".venv\Scripts\python.exe" (
  echo [setup] First run: creating virtual environment...
  python -m venv .venv
  if errorlevel 1 ( echo [ERROR] Could not create virtual environment. & pause & exit /b 1 )
)

set "PY=.venv\Scripts\python.exe"

REM --- Install dependencies (quick if already installed) ---
echo [setup] Checking dependencies...
"%PY%" -m pip install --upgrade pip >nul 2>nul
"%PY%" -m pip install -r requirements.txt
if errorlevel 1 ( echo [ERROR] Could not install dependencies. Check your internet connection. & pause & exit /b 1 )

REM --- Database + sample data + admin user ---
echo [setup] Preparing database...
"%PY%" manage.py migrate --noinput
"%PY%" manage.py bootstrap

echo.
echo ================================================================
echo    Starting SchemeSetu ...
echo    Open in browser:  http://127.0.0.1:8000
echo    Login / Sign Up:  http://127.0.0.1:8000/auth/login/
echo    Admin panel:      http://127.0.0.1:8000/admin  (admin / admin123)
echo    Alert Centre:     http://127.0.0.1:8000/notifications/
echo    Sync scholarships + notify:
echo       python manage.py sync_scholarships --notify-all
echo    Run daemon (auto-sync every 6 h):
echo       python manage.py sync_scholarships --daemon --interval 360
echo    Press CTRL + C in this window to stop the server.
echo ================================================================
echo.

REM --- Open the browser, then run the server ---
start "" http://127.0.0.1:8000
"%PY%" manage.py runserver 127.0.0.1:8000

pause
