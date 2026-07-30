# MDC Notification Service & Background Worker Guide

This guide details how to run the notification processor as an isolated background service on **Windows**, **Linux**, **Linux Crontab**, or **Linux Systemd Service**.

---

## 1. Django Management Command Usage

### A. One-Shot Execution (Ideal for Linux Crontab)
Processes all currently unsent notifications in MongoDB and exits immediately:

```bash
python manage.py process_notifications
```

### B. Daemon Mode (Continuous Background Polling every 5 Seconds)
Runs in an infinite loop polling MongoDB every 5 seconds (or custom interval):

```bash
python manage.py process_notifications --daemon --interval 5
```

---

## 2. Windows Service / Batch Script (`run_notification_worker.bat`)

Double-click `run_notification_worker.bat` or run it from CMD:

```cmd
run_notification_worker.bat
```

- Automatically activates virtual environment (`venv\Scripts\activate.bat`).
- Starts `process_notifications --daemon --interval 5`.

---

## 3. Linux Shell Script (`run_notification_worker.sh`)

Make the script executable and run it on Linux / Apache node (`node221456-env-5683222`):

```bash
chmod +x run_notification_worker.sh
./run_notification_worker.sh
```

---

## 6. Multi-Service Startup Scripts (Django Server + Worker Daemon)

### A. Windows Startup Script (`run_all_services_win.bat`)
Runs Django Server on **Port 8000** and Notification Worker Daemon in separate CMD windows:

```cmd
run_all_services_win.bat
```

### B. Linux Startup Script (`run_all_services_linux.sh`)
Runs Django Server on **Port 2526** and Notification Worker Daemon in background (`nohup`):

```bash
chmod +x run_all_services_linux.sh
./run_all_services_linux.sh
```
- Django Server Log: `django_server.log`
- Notification Worker Log: `notification_worker.log`

