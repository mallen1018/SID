#!/bin/bash
# One-time setup: fix Full Disk Access so double-clicking "SID Vendor Spawner.app"
# can write to ~/Documents/SID without the Errno 1 / Operation not permitted error.
#
# macOS TCC (Transparency, Consent, Control) blocks .app bundles from writing
# to Documents/Desktop/Downloads/iCloud Drive unless the user has explicitly
# granted Full Disk Access. Because our .app uses a bash launcher that execs
# the system Python interpreter, macOS attributes the permission request to
# Python's RESOLVED binary path, not to the .app itself — so granting FDA to
# the .app alone doesn't help.
#
# This helper:
#   1. Ad-hoc codesigns the .app (gives TCC a stable identity for it)
#   2. Finds which Python the launcher will use and resolves its real path
#   3. Opens a Finder window at that Python binary's folder
#   4. Opens System Settings directly to Full Disk Access
#
# You drag the Python binary from the Finder window into the FDA list,
# toggle it on, and you're done forever.

set -e

APP="/Users/melissaallen/Documents/SID/SID Vendor Spawner.app"

echo "=================================================="
echo "  SID Vendor Spawner — Full Disk Access Setup"
echo "=================================================="
echo ""

# ─── Step 1: Ad-hoc codesign the .app ───────────────────────
echo "Step 1: Ad-hoc code-signing the app…"
codesign --force --deep --sign - "$APP" 2>&1 && echo "  ✓ signed" || echo "  ⚠ codesign warning (usually OK)"
echo ""

# ─── Step 2: Find the Python the launcher will pick ─────────
echo "Step 2: Finding the Python interpreter the launcher uses…"
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
    echo "  ✗ No usable Python 3 with Tkinter found."
    echo "    Install Python 3 from python.org and re-run this script."
    exit 1
fi

REAL_PYTHON="$(readlink -f "$PYTHON" 2>/dev/null || realpath "$PYTHON" 2>/dev/null || echo "$PYTHON")"
REAL_DIR="$(dirname "$REAL_PYTHON")"

echo "  ✓ Launcher will use:   $PYTHON"
echo "  ✓ Resolves to:         $REAL_PYTHON"
echo ""

# ─── Step 3: Open Finder at the Python binary's folder ──────
echo "Step 3: Opening Finder at the Python binary so you can drag it…"
open -R "$REAL_PYTHON"
echo ""

# ─── Step 4: Open System Settings → Full Disk Access ────────
echo "Step 4: Opening Full Disk Access settings…"
open "x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles" 2>/dev/null || \
    open "/System/Library/PreferencePanes/Security.prefPane"
echo ""

echo "=================================================="
echo "  NEXT STEPS (do these in the windows that just opened):"
echo "=================================================="
echo ""
echo "  1. In Full Disk Access, click the + button."
echo "  2. When the picker opens, drag this file from the"
echo "     Finder window into it:"
echo ""
echo "       $(basename "$REAL_PYTHON")"
echo ""
echo "     (It's highlighted in the Finder window that just opened.)"
echo ""
echo "  3. Click Open in the picker."
echo "  4. Toggle the switch ON next to it."
echo "  5. Close System Settings."
echo ""
echo "  You're done. Double-click \"SID Vendor Spawner.app\" —"
echo "  it will now work without any Terminal commands."
echo ""
echo "=================================================="
echo ""
echo "(Press Return to close this window.)"
read -r _
