#!/bin/bash
# Start the collector and a Cloudflare quick tunnel in tmux session "gestures".
#   CLASS_TOKEN=xyz ./run.sh          # DATA_DIR defaults to ~/gestures-data
#   tmux attach -t gestures           # watch; the tunnel URL is in window "tunnel"
#   ./run.sh url                      # print the public URL
set -e
cd "$(dirname "$0")"
LOG=/tmp/gestures-tunnel.log

if [ "$1" = "url" ]; then grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' "$LOG" | tail -1; exit; fi

: "${CLASS_TOKEN:?set CLASS_TOKEN}"
export DATA_DIR="${DATA_DIR:-$HOME/gestures-data}"
PORT="${PORT:-8000}"

tmux kill-session -t gestures 2>/dev/null || true
rm -f "$LOG"
uv sync -q
tmux new-session -d -s gestures -n server \
  "CLASS_TOKEN='$CLASS_TOKEN' DATA_DIR='$DATA_DIR' uv run uvicorn app:app --host 127.0.0.1 --port $PORT --proxy-headers --forwarded-allow-ips='*'; read"
tmux new-window -t gestures -n tunnel \
  "cloudflared tunnel --no-autoupdate --url http://localhost:$PORT 2>&1 | tee $LOG; read"

for i in $(seq 30); do
  URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' "$LOG" 2>/dev/null | tail -1)
  [ -n "$URL" ] && break; sleep 1
done
echo "phone:     $URL/?t=$CLASS_TOKEN"
echo "dashboard: $URL/dashboard"
echo "export:    $URL/api/export?t=$CLASS_TOKEN"
