#!/usr/bin/env bash
# Stop all PYREGUARD services
set -euo pipefail

stop_pid() {
  local name=$1
  local pidfile=$2
  if [ -f "$pidfile" ]; then
    pid=$(cat "$pidfile")
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid"
      echo "[INFO] Stopped $name (PID $pid)"
    fi
    rm -f "$pidfile"
  fi
}

stop_pid "Backend"  backend.pid
stop_pid "Frontend" frontend.pid
echo "[INFO] All services stopped."
