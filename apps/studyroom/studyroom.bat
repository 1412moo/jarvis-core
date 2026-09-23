@echo off
rem Jarvis Studyroom: double-click to start the local server and open the browser.
cd /d "%~dp0"
python -B run_web_app.py
pause
