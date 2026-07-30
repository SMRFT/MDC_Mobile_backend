#!/bin/bash
# Script to launch all MDC Mobile Backend services on Linux (Port 2526)
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d "../venv" ]; then
    source ../venv/bin/activate
fi

echo "========================================================"
echo "  Starting MDC Mobile Backend Services (Linux)          "
echo "========================================================"

echo "Starting Django Server on port 2526..."
nohup python manage.py runserver 0.0.0.0:2526 --settings=MDC_Mobile_backend.settings-test > django_server.log 2>&1 &
DJANGO_PID=$!
echo "Django Server started on port 2526 (PID: $DJANGO_PID)"

echo "Starting Notification Worker Daemon..."
nohup python manage.py process_notifications --daemon --interval 5 > notification_worker.log 2>&1 &
WORKER_PID=$!
echo "Notification Worker Daemon started (PID: $WORKER_PID)"

echo "========================================================"
echo "Services running in background:"
echo "  - Django Server (Port 2526, Log: django_server.log)"
echo "  - Notification Worker (Daemon, Log: notification_worker.log)"
echo "========================================================"
