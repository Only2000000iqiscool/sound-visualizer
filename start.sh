#!/usr/bin/env bash
# Sound Visualizer – Desktop-Starter (Doppelklick oder .desktop-Verknüpfung)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}" 2>/dev/null || realpath "${BASH_SOURCE[0]}")")" && pwd)"
cd "$SCRIPT_DIR"

LOG_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/sound-visualizer"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/startup.log"
APP_LOG="$LOG_DIR/latest.log"

export DISPLAY="${DISPLAY:-:0}"
export QT_FFMPEG_DECODING_HW_DEVICE_TYPES="${QT_FFMPEG_DECODING_HW_DEVICE_TYPES:-,}"
export QT_FFMPEG_ENCODING_HW_DEVICE_TYPES="${QT_FFMPEG_ENCODING_HW_DEVICE_TYPES:-,}"
export QT_LOGGING_RULES="${QT_LOGGING_RULES:-qt.multimedia.*=false;qt.qpa.*=false}"

show_error() {
    local msg="$1"
    {
        echo "----- $(date -Iseconds) -----"
        echo "$msg"
    } >>"$LOG_FILE"

    if command -v zenity >/dev/null 2>&1; then
        zenity --error --title="Sound Visualizer" --text="${msg}

Log: ${LOG_FILE}" 2>/dev/null || true
    elif command -v kdialog >/dev/null 2>&1; then
        kdialog --error "${msg}

Log: ${LOG_FILE}" 2>/dev/null || true
    elif command -v notify-send >/dev/null 2>&1; then
        notify-send "Sound Visualizer" "$msg" 2>/dev/null || true
    fi
}

if ! command -v python3 >/dev/null 2>&1; then
    show_error "Python 3 wurde nicht gefunden.

Installiere mit: sudo pacman -S python"
    exit 1
fi

if ! python3 -c "import PyQt6" 2>>"$LOG_FILE"; then
    show_error "PyQt6 fehlt.

Installiere mit:
sudo pacman -S python-pyqt6 python-numpy python-pyaudio ffmpeg"
    exit 1
fi

{
    echo "----- $(date -Iseconds) start -----"
    echo "cwd: $SCRIPT_DIR"
    echo "display: $DISPLAY"
} >>"$LOG_FILE"

if python3 run.py >>"$LOG_FILE" 2>&1; then
    exit 0
fi

show_error "Sound Visualizer konnte nicht starten.

App-Log (bitte mitschicken):
${APP_LOG}

Starter-Log:
${LOG_FILE}"
exit 1
