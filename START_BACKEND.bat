@echo off
title Seismic Checker - Backend Only
color 0B
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║  BACKEND SERVER (FastAPI)                ║
echo  ║  http://localhost:8005                   ║
echo  ║  API Docs: http://localhost:8005/docs    ║
echo  ╚══════════════════════════════════════════╝
echo.

cd /d "%~dp0"

:: Setup venv if needed
if not exist "backend\venv" (
    echo [SETUP] Creating virtual environment...
    python -m venv backend\venv
    call backend\venv\Scripts\activate.bat
    echo [SETUP] Installing dependencies...
    pip install -r backend\requirements.txt
) else (
    call backend\venv\Scripts\activate.bat
)

cd backend
echo [START] Starting FastAPI backend with auto-reload...
echo.
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8005
pause
