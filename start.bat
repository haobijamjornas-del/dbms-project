@echo off
cd /d "%~dp0"

python start.py
if errorlevel 1 (
    echo.
    echo  "python" was not found. Trying "py" instead...
    py start.py
)
pause
