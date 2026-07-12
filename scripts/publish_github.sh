#!/usr/bin/env bash
# Erstellt ein GitHub-Repository und pusht den Code.
set -euo pipefail
cd "$(dirname "$0")/.."

REPO_NAME="${1:-sound-visualizer}"
VISIBILITY="${2:-public}"

if ! command -v gh >/dev/null 2>&1; then
  echo "GitHub CLI (gh) ist nicht installiert."
  echo "Installieren: sudo pacman -S github-cli"
  echo "Dann: gh auth login"
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "Bitte zuerst anmelden: gh auth login"
  exit 1
fi

if git remote get-url origin >/dev/null 2>&1; then
  echo "Remote 'origin' existiert bereits."
else
  gh repo create "$REPO_NAME" --"$VISIBILITY" --source=. --remote=origin --description "Native PyQt6 Sound Visualizer with 17 modes"
fi

git push -u origin HEAD
echo "Fertig: $(gh repo view --json url -q .url)"
