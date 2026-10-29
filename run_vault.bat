@echo off
REM Matrimony Vault launcher for Windows (avoids PATH issues with streamlit.exe)
cd /d "%~dp0"
python -m streamlit run vault\app.py
if errorlevel 1 (
  echo.
  echo If Python was not found, try:  py -m streamlit run vault\app.py
  pause
)
