@echo off
title JARVIS Glass Media Server & Personal Cloud Drive
cd /d "%~dp0"

echo ===================================================================
echo     JARVIS Glass Media Server, YouTube Scraper & Cloud Drive
echo ===================================================================
echo.
echo [*] Checking Python environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Python is not installed or not in PATH! Please install Python 3.10+
    pause
    exit /b 1
)

echo [*] Launching server on port 8000...
echo [*] Opening dashboard in your default browser...
start "" http://localhost:8000

echo.
echo [*] Server is running. Press CTRL+C to stop.
echo ===================================================================
echo.

python app.py

pause
