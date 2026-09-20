#!/usr/bin/env bash
# Stops the detached KCNA Exam Prep app started by start.sh
cd "$(dirname "$0")"

if [ ! -f app.pid ]; then
    echo "No app.pid file found — is the app running via ./start.sh?"
    exit 1
fi

PID="$(cat app.pid)"
if kill -0 "$PID" 2>/dev/null; then
    kill "$PID"
    rm -f app.pid
    echo "Stopped (PID $PID)."
else
    echo "Process $PID is not running. Removing stale app.pid."
    rm -f app.pid
fi
