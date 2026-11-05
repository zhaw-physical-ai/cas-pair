#!/bin/bash
# Run the gestures server in the foreground on all interfaces, e.g. on a RunPod pod.
#   CLASS_TOKEN=<word> ./serve.sh            # port 8000, data in ~/gestures-data
#   CLASS_TOKEN=<word> PORT=8080 DATA_DIR=/workspace/gestures-data ./serve.sh
# Phones need HTTPS for their motion sensors: put a proxy in front (RunPod's HTTP port proxy, or
# `cloudflared tunnel --url http://localhost:8000`), see HOSTING.md.
set -e
cd "$(dirname "$0")"
: "${CLASS_TOKEN:?set CLASS_TOKEN to a word of your choice}"
export CLASS_TOKEN DATA_DIR="${DATA_DIR:-$HOME/gestures-data}"
command -v uv >/dev/null || { curl -LsSf https://astral.sh/uv/install.sh | sh; export PATH="$HOME/.local/bin:$PATH"; }
exec uv run uvicorn app:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips='*'
