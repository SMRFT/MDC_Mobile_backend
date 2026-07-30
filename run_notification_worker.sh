#!/bin/bash
# MDC Notification Background Worker Script for Linux / Production
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d "../venv" ]; then
    source ../venv/bin/activate
fi

echo "========================================================"
echo "  MDC Notification Background Worker Daemon (Linux)    "
echo "========================================================"
python manage.py process_notifications --daemon --interval 5
