#!/usr/bin/env bash
# Starts the KCNA Exam Prep app in the background (detached) and writes
# its output to app.log and its process id to app.pid.
set -e
cd "$(dirname "$0")"

if [ -f app.pid ] && kill -0 "$(cat app.pid)" 2>/dev/null; then
    echo "Already running (PID $(cat app.pid)). Run ./stop.sh first if you want to restart."
    exit 1
fi

# Seed the database on first run
python3 -c "import app; app.ensure_seeded()"

if command -v gunicorn >/dev/null 2>&1; then
    # Production-grade WSGI server (preferred: handles concurrent users properly)
    nohup gunicorn -w 2 -b 0.0.0.0:5000 --daemon --pid app.pid --access-logfile app.log --error-logfile app.log app:app
    sleep 1
else
    # Fallback: Flask's built-in dev server, backgrounded manually
    nohup python3 app.py > app.log 2>&1 &
    disown
    echo $! > app.pid
    sleep 1
fi
echo "Started KCNA Exam Prep (PID $(cat app.pid))."
echo "Visit http://127.0.0.1:5000"
echo "Logs: tail -f app.log"
