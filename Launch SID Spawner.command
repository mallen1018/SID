#!/bin/bash
# Double-click launcher for SID Vendor Spawner.
#
# This bypasses the .app bundle's Full Disk Access issue by launching the
# Spawner through Terminal directly. Terminal already has Full Disk Access
# (you've been using it all along), so no TCC prompts, no Errno 1 errors.
#
# Double-click this file to open the Spawner. That's the whole user flow.

APP_PY="/Users/melissaallen/Documents/SID/SID Vendor Spawner.app/Contents/Resources/app.py"

# Find a usable Python 3 with Tkinter
CANDIDATES=(
    "/opt/homebrew/bin/python3.11"
    "/opt/homebrew/bin/python3.12"
    "/opt/homebrew/bin/python3.13"
    "/opt/homebrew/bin/python3"
    "/usr/local/bin/python3.11"
    "/usr/local/bin/python3.12"
    "/usr/local/bin/python3"
    "/usr/bin/python3"
)

PYTHON=""
for p in "${CANDIDATES[@]}"; do
    if [ -x "$p" ] && "$p" -c "import tkinter" >/dev/null 2>&1; then
        PYTHON="$p"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    osascript -e 'display dialog "SID Vendor Spawner could not find a Python 3 install with Tkinter. Install Python 3 from python.org (that build includes Tkinter) and try again." buttons {"OK"} with icon caution with title "SID Vendor Spawner"'
    exit 1
fi

exec "$PYTHON" "$APP_PY"
