@echo off
title Seismic Deliverable AI Checker - Starting...
color 0A
echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║     SEISMIC DELIVERABLE AI CHECKER                      ║
echo  ║     Starting Development Server...                      ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

:: Check Python
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Please install Python 3.11+
    pause
    exit /b 1
)

:: Check Node
where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found! Please install Node.js 18+
    pause
    exit /b 1
)

:: Install Python dependencies if needed
if not exist "backend\venv" (
    echo [SETUP] Creating Python virtual environment...
    python -m venv backend\venv
    echo [SETUP] Installing Python dependencies...
    call backend\venv\Scripts\activate.bat
    pip install -r backend\requirements.txt
) else (
    call backend\venv\Scripts\activate.bat
)

:: Install frontend dependencies if needed
if not exist "frontend\node_modules" (
    echo [SETUP] Installing frontend dependencies...
    cd frontend
    call npm install
    cd ..
)

:: Install root dependencies if needed
if not exist "node_modules" (
    echo [SETUP] Installing root dependencies...
    call npm install
)

echo.
echo  ┌──────────────────────────────────────────────────────────┐
echo  │  Starting Backend (FastAPI) on http://localhost:8005     │
echo  │  Starting Frontend (Vite)   on http://localhost:5176     │
echo  │                                                          │
echo  │  Press Ctrl+C to stop all servers                        │
echo  └──────────────────────────────────────────────────────────┘
echo.

:: Start backend and frontend concurrently
start "Seismic Checker - Backend" cmd /k "cd /d %~dp0backend && ..\backend\venv\Scripts\activate.bat && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8005"

:: Wait a moment for backend to initialize
timeout /t 3 /noq >nul

start "Seismic Checker - Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

:: Wait for frontend to be ready then open browser
timeout /t 5 /noq >nul
echo.
echo  [OK] Opening browser at http://localhost:5176
start http://localhost:5176

echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║  Servers are running! Close the terminal windows to     ║
echo  ║  stop them, or press any key to stop all.               ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.
pause
taskkill /FI "WINDOWTITLE eq Seismic Checker - Backend*" >nul 2>&1
taskkill /FI "WINDOWTITLE eq Seismic Checker - Frontend*" >nul 2>&1
