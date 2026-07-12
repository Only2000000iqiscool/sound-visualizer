#!/usr/bin/env bash
# Legt Verknüpfungen auf dem Schreibtisch und im KDE-Anwendungsstarter an.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}" 2>/dev/null || realpath "${BASH_SOURCE[0]}")")" && pwd)"
APPS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"

if [ -d "${XDG_DESKTOP_DIR:-}" ]; then
    DESKTOP_DIR="$XDG_DESKTOP_DIR"
elif [ -d "$HOME/Schreibtisch" ]; then
    DESKTOP_DIR="$HOME/Schreibtisch"
elif [ -d "$HOME/Desktop" ]; then
    DESKTOP_DIR="$HOME/Desktop"
else
    DESKTOP_DIR="$HOME"
fi

DESKTOP_TARGET="$DESKTOP_DIR/Sound Visualizer.desktop"
MENU_TARGET="$APPS_DIR/sound-visualizer.desktop"

chmod +x "$SCRIPT_DIR/start.sh"
mkdir -p "$APPS_DIR"

render_desktop() {
    sed "s|@PROJECT_DIR@|$SCRIPT_DIR|g" "$SCRIPT_DIR/sound-visualizer.desktop"
}

render_desktop >"$DESKTOP_TARGET"
chmod +x "$DESKTOP_TARGET"

render_desktop >"$MENU_TARGET"
chmod +x "$MENU_TARGET"

if command -v gio >/dev/null 2>&1; then
    gio set "$DESKTOP_TARGET" metadata::trusted true 2>/dev/null || true
fi

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APPS_DIR" 2>/dev/null || true
fi

if command -v kbuildsycoca6 >/dev/null 2>&1; then
    kbuildsycoca6 --noincremental >/dev/null 2>&1 || true
elif command -v kbuildsycoca5 >/dev/null 2>&1; then
    kbuildsycoca5 --noincremental >/dev/null 2>&1 || true
fi

echo "Schreibtisch-Verknüpfung: $DESKTOP_TARGET"
echo "KDE-Anwendungsstarter:    $MENU_TARGET"
echo "Starte die App über das KDE-Menü unter „Sound Visualizer“ oder per Doppelklick auf dem Schreibtisch."
