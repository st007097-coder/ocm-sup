#!/bin/bash
# Watchdog script for Triple-Stream Search API
# Restarts the API if it crashes

API_PORT=5000
API_SCRIPT="/root/.openclaw/workspace/OCM-Sup/scripts/search_api.py"
LOG_FILE="/tmp/search-api.log"
PID_FILE="/tmp/search-api.pid"

check_api() {
    curl -sf http://localhost:${API_PORT}/health > /dev/null 2>&1
    return $?
}

start_api() {
    echo "[$(date)] API crashed, restarting..." >> $LOG_FILE
    nohup /root/.openclaw/venv/bin/python3 $API_SCRIPT --host 0.0.0.0 --port $API_PORT >> $LOG_FILE 2>&1 &
    echo $! > $PID_FILE
    echo "[$(date)] API started with PID $(cat $PID_FILE)" >> $LOG_FILE
}

# Initial check
if ! check_api; then
    echo "[$(date)] API not running, starting..." >> $LOG_FILE
    nohup /root/.openclaw/venv/bin/python3 $API_SCRIPT --host 0.0.0.0 --port $API_PORT >> $LOG_FILE 2>&1 &
    echo $! > $PID_FILE
    echo "[$(date)] API started with PID $(cat $PID_FILE)" >> $LOG_FILE
fi

# Monitor loop
while true; do
    sleep 30
    if ! check_api; then
        start_api
    fi
done
