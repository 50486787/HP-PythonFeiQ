@echo off
cd /d "%~dp0"
uv venv
uv pip install rsa PyQt5
echo Done.
pause
