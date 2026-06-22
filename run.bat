@echo off
REM Windows launcher - double-click this file to start the dashboard.
cd /d "%~dp0"

echo Portfolio Dashboard
echo ------------------------------------

where python >nul 2>nul
if errorlevel 1 (
  echo Python is not installed.
  echo Install it from https://www.python.org/downloads/
  echo IMPORTANT: tick "Add Python to PATH" during install, then run this again.
  pause
  exit /b 1
)

echo Installing dependencies (first run only, ~1 min)...
python -m pip install --quiet --disable-pip-version-check -r requirements.txt

echo.
echo Starting... your browser will open at http://localhost:8501
echo Close this window to stop the dashboard.
echo.
python -m streamlit run app.py
pause
