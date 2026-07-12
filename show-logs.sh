#!/usr/bin/env bash
# Zeigt die aktuellen App-Logs an (zum Weiterschicken bei Fehlern).

LOG_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/sound-visualizer"
LATEST="$LOG_DIR/latest.log"

if [ ! -f "$LATEST" ]; then
    echo "Kein Log gefunden. Starte die App einmal und versuche den Fehler erneut."
    echo "Erwarteter Pfad: $LATEST"
    exit 1
fi

echo "=== Sound Visualizer Log ==="
echo "Datei: $LATEST"
echo "==========================="
cat "$LATEST"
