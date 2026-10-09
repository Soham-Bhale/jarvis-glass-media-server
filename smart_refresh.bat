@echo off
title JARVIS Smart Refresh - Auto Sync Latest Videos
cd /d "%~dp0"

echo ===================================================================
echo   JARVIS Smart Refresh - Auto Download Latest Channel Videos
echo ===================================================================
echo.
echo [1/3] Stopping any running server on port 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo [*] Killing old server [PID %%a]...
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 1 >nul

echo [2/3] Checking for new YouTube videos (yt-dlp auto-skips already downloaded)...
python scraper.py
if %errorlevel% neq 0 (
    echo [!] Scraper encountered an error, but continuing...
)

echo.
echo [3/3] Starting JARVIS Media Server...
start "" http://localhost:8000
python app.py

pause
