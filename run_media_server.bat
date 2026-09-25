@echo off
title JARVIS Glass Media Server & Cloud Drive
cd /d "%~dp0"

echo =========================================================
echo    💎 JARVIS Glass Media Server & Personal Cloud Drive
echo =========================================================
echo.
echo [*] Starting server on port 8000...
echo.

python app.py

pause
