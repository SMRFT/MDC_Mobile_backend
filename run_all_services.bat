@echo off
title Starting MDC Mobile Backend Services (Windows)
echo Starting MDC Mobile Backend Services...

echo Starting Django Server on port 8000...
start "MDC Django Server (Port 8000)" cmd /k "venv\Scripts\python manage.py runserver 0.0.0.0:8000"

echo Starting Notification Worker Daemon...
start "MDC Notification Worker (Daemon)" cmd /k "venv\Scripts\python manage.py process_notifications --daemon --interval 5"

echo Backend services started successfully. You can close this main window.
pause
