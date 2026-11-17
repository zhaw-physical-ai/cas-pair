#!/bin/bash
# Start the SO-101 phone teleop server.
#   TOKEN=<word> ./serve.sh                     # port 8001, episodes in ~/teleop-data/episodes
#   TOKEN=<word> PORT=8002 DATA_DIR=/workspace/teleop-data ./serve.sh
# Phones need an https address: in a second terminal run
#   cloudflared tunnel --url http://localhost:8001
set -e
cd "$(dirname "$0")"
: "${TOKEN:?set TOKEN to a word of your choice (it protects the data download)}"
export TOKEN DATA_DIR="${DATA_DIR:-$HOME/teleop-data}"
exec uv run uvicorn server:app --host 127.0.0.1 --port "${PORT:-8001}" --proxy-headers --forwarded-allow-ips='*'
