@echo off
rem Opens the QudAI console (no terminal window). Needs the same Python that runs brain.py.
cd /d "%~dp0"
start "" pythonw tools\qudai_console.py
