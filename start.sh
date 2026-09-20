#!/usr/bin/env bash
# Starts the KCNA Exam Prep app in the background (detached) and writes
# its output to app.log and its process id to app.pid.
#
# If a local ./venv virtual environment exists, its python/gunicorn are
# used automatically. Otherwise the system python3/gunicorn are used.
#
# First-time setup, if you don't already have Flask installed:
#     python3 -m venv venv
#     venv/bin/pip install -r requirements.txt
set -e
cd "$(dirname "$0")"

if [ -f app.pid ] && kill -0 "$(cat app.pid)" 2>/dev/null; then
    echo "Already running (PID $(cat app.pid)). Run ./stop.sh first if you want to restart."
    exit 1
fi

# Prefer a local virtual environment if one has been set up
if [ -x "venv/bin/python3" ]; then
    PYTHON="venv/bin/python3"
    GUNICORN="venv/bin/gunicorn"
else
    PYTHON="python3"
    GUNICORN="gunicorn"
fi

# Check dependencies are installed before doing anything else
if ! "$PYTHON" -c "import flask" >/dev/null 2>&1; then
    echo "Error: the 'flask' module isn't installed for $PYTHON."
    echo ""
    if [ -x "venv/bin/python3" ]; then
        echo "Your venv exists but dependencies aren't installed in it. Run:"
        echo ""
        echo "    venv/bin/pip install -r requirements.txt"
    else
        echo "Set up a virtual environment (recommended, avoids system Python conflicts):"
        echo ""
        echo "    python3 -m venv venv"
        echo "    venv/bin/pip install -r requirements.txt"
        echo ""
        echo "Then run ./start.sh again."
    fi
    echo ""
    exit 1
fi

# Seed the database on first run
"$PYTHON" -c "import app; app.ensure_seeded()"

if command -v "$GUNICORN" >/dev/null 2>&1; then
    # Production-grade WSGI server (preferred: handles concurrent users properly)
    nohup "$GUNICORN" -w 2 -b 0.0.0.0:5000 --daemon --pid app.pid --access-logfile app.log --error-logfile app.log app:app
    sleep 1
else
    # Fallback: Flask's built-in dev server, backgrounded manually
    nohup "$PYTHON" app.py > app.log 2>&1 &
    disown
    echo $! > app.pid
    sleep 1
fi
echo "Started KCNA Exam Prep (PID $(cat app.pid))."
echo "Visit http://127.0.0.1:5000"
echo "Logs: tail -f app.log"
