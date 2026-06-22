#!/usr/bin/env bash
# Boot the full AI Integration Sandbox (mock APIs, service, dashboard).
# Usage: ./run-sandbox.sh
#        ./run-sandbox.sh --no-ui

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

NO_UI=false
for arg in "$@"; do
  case "$arg" in
    --no-ui) NO_UI=true ;;
    -h|--help)
      echo "Usage: $0 [--no-ui]"
      exit 0
      ;;
  esac
done

if [[ ! -d .venv ]]; then
  echo "No .venv found — running setup..."
  python tasks.py setup
fi

cleanup() {
  echo ""
  echo "Stopping sandbox..."
  for pid in $(jobs -p); do
    kill "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT INT TERM

echo ""
echo "Starting AI Integration Sandbox..."
echo ""

python tasks.py mock-apis &
sleep 2
python tasks.py run &

if [[ "$NO_UI" == false ]]; then
  python tasks.py ui &
fi

echo "  Mock APIs:  http://127.0.0.1:9000"
echo "  Service:    http://127.0.0.1:8000/docs"
if [[ "$NO_UI" == false ]]; then
  echo "  Dashboard:  http://127.0.0.1:5173"
fi
echo ""
echo "Press Ctrl+C to stop all services."

wait
