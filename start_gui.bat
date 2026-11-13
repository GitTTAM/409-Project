@echo off
cd /d "%~dp0"
python3.14 gui.py
if errorlevel 1 pause
