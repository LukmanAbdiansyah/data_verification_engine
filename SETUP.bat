@echo off
title Seismic Checker - Initial Setup
color 0A
echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║  SEISMIC DELIVERABLE AI CHECKER                         ║
echo  ║  First-Time Setup                                       ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

:: ── Check Prerequisites ──
echo [CHECK] Checking prerequisites...
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo  [X] Python      NOT FOUND - Please install Python 3.11+
    echo      Download: https://www.python.org/downloads/
    set MISSING=1
) else (
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo  [OK] %%i
)

where node >nul 2>&1
if errorlevel 1 (
    echo  [X] Node.js     NOT FOUND - Please install Node.js 18+
    echo      Download: https://nodejs.org/
    set MISSING=1
) else (
    for /f "tokens=*" %%i in ('node --version 2^>^&1') do echo  [OK] Node.js %%i
)

where npm >nul 2>&1
if errorlevel 1 (
    echo  [X] npm         NOT FOUND
    set MISSING=1
) else (
    for /f "tokens=*" %%i in ('npm --version 2^>^&1') do echo  [OK] npm %%i
)

if defined MISSING (
    echo.
    echo [ERROR] Missing prerequisites! Install them first.
    pause
    exit /b 1
)

echo.
echo ──────────────────────────────────────────────────────────
echo.

:: ── Step 1: Python Virtual Environment ──
echo [1/4] Setting up Python virtual environment...
if not exist "backend\venv" (
    python -m venv backend\venv
    echo       Created backend\venv
) else (
    echo       Already exists - skipping
)

call backend\venv\Scripts\activate.bat

:: ── Step 2: Python Dependencies ──
echo [2/4] Installing Python dependencies...
pip install -r backend\requirements.txt --quiet
echo       Done!

:: ── Step 3: Root Node Dependencies ──
echo [3/4] Installing root Node.js dependencies (Electron)...
call npm install
echo       Done!

:: ── Step 4: Frontend Dependencies ──
echo [4/4] Installing frontend dependencies (React + Vite)...
cd frontend
call npm install
cd ..
echo       Done!

echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║  SETUP COMPLETE!                                        ║
echo  ║                                                         ║
echo  ║  Available shortcuts:                                   ║
echo  ║                                                         ║
echo  ║  START_APP.bat       - Start Backend + Frontend (Web)   ║
echo  ║  START_ELECTRON.bat  - Start as Desktop App             ║
echo  ║  START_BACKEND.bat   - Backend only                     ║
echo  ║  START_FRONTEND.bat  - Frontend only                    ║
echo  ║  RUN_TESTS.bat       - Run backend tests                ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.
pause
