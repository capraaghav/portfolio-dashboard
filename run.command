#!/bin/bash
# macOS launcher — double-click this file in Finder to start the dashboard.
# (First time: right-click → Open, to get past the "unidentified developer" prompt.)
cd "$(dirname "$0")" || exit 1

echo "📈  Portfolio Dashboard"
echo "------------------------------------"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is not installed."
  echo "Install it from https://www.python.org/downloads/ and run this again."
  read -r -p "Press Enter to close…" _
  exit 1
fi

echo "Installing dependencies (first run only, ~1 min)…"
python3 -m pip install --user --quiet --disable-pip-version-check -r requirements.txt

echo ""
echo "Starting… your browser will open at http://localhost:8501"
echo "Close this window (or press Ctrl+C) to stop the dashboard."
echo ""
python3 -m streamlit run app.py
