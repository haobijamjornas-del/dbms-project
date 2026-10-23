#!/bin/bash
cd "$(dirname "$0")" || exit 1

if command -v python3 >/dev/null 2>&1; then
    python3 start.py
else
    python start.py
fi

echo ""
echo "  Press Return to close this window."
read -r
