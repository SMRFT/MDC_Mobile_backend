@echo off
title MDC Notification Background Worker
echo ========================================================
echo   MDC Notification Background Worker Service (Windows)
echo ========================================================
cd /d "%~dp0"

if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo Virtual environment venv not found in %CD%
)

python manage.py process_notifications --daemon --interval 5
pause
