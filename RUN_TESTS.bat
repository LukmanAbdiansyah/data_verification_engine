@echo off
title Seismic Checker - Tests
color 0C
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║  Running Backend Tests                   ║
echo  ╚══════════════════════════════════════════╝
echo.

cd /d "%~dp0"

if not exist "backend\venv" (
    echo [ERROR] Run SETUP.bat first!
    pause
    exit /b 1
)

call backend\venv\Scripts\activate.bat
cd backend

echo [TEST] Running pytest...
echo.
python -m pytest tests/ -v --tb=short
echo.
pause
