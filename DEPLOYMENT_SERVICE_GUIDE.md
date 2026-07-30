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

## 4. Linux Crontab Configuration (Every Minute One-Shot)

If you prefer Linux `cron` instead of a continuous daemon:

1. Open crontab editor:
   ```bash
   crontab -e
   ```
2. Add this line to run the command every minute:
   ```cron
   * * * * * cd /home/apache/MDC_Mobile_backend && /home/apache/MDC_Mobile_backend/venv/bin/python manage.py process_notifications >> /home/apache/MDC_Mobile_backend/notification_cron.log 2>&1
   ```

---

## 5. Linux Systemd 24/7 Background Service (`mdc_notification_worker.service`)

To run the worker as an automatic 24/7 Linux system service that restarts on reboot:

1. Copy service file to `/etc/systemd/system/`:
   ```bash
   sudo cp mdc_notification_worker.service /etc/systemd/system/
   ```
2. Reload systemd daemon:
   ```bash
   sudo systemctl daemon-reload
   ```
3. Enable and start service:
   ```bash
   sudo systemctl enable mdc_notification_worker.service
   sudo systemctl start mdc_notification_worker.service
   ```
4. Check service status:
   ```bash
   sudo systemctl status mdc_notification_worker.service
   ```
5. View live worker logs:
   ```bash
   sudo journalctl -u mdc_notification_worker.service -f
   ```
