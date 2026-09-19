@echo off
title Seismic Checker - Electron Desktop App
color 0E
echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║  SEISMIC DELIVERABLE AI CHECKER                         ║
echo  ║  Launching as Electron Desktop Application...           ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

:: Setup venv if needed
if not exist "backend\venv" (
    echo [SETUP] Creating virtual environment...
    python -m venv backend\venv
    call backend\venv\Scripts\activate.bat
    pip install -r backend\requirements.txt
) else (
    call backend\venv\Scripts\activate.bat
)

:: Install root deps if needed
if not exist "node_modules" (
    echo [SETUP] Installing root dependencies...
    call npm install
)

:: Install frontend deps if needed
if not exist "frontend\node_modules" (
    echo [SETUP] Installing frontend dependencies...
    cd frontend
    call npm install
    cd ..
)

:: Start backend in background
echo [START] Starting backend server...
start /B "Backend" cmd /c "cd /d %~dp0backend && ..\backend\venv\Scripts\activate.bat && python -m uvicorn app.main:app --host 127.0.0.1 --port 8005"
timeout /t 3 /noq >nul

:: Start frontend in background
echo [START] Starting frontend dev server...
start /B "Frontend" cmd /c "cd /d %~dp0frontend && npm run dev"
timeout /t 5 /noq >nul

:: Compile and launch Electron
echo [START] Compiling Electron TypeScript...
call npx tsc -p tsconfig.electron.json 2>nul

echo [START] Launching Electron window...
set NODE_ENV=development
call npx electron .

:: Cleanup on close
echo.
echo [STOP] Cleaning up servers...
taskkill /FI "WINDOWTITLE eq Backend*" >nul 2>&1
taskkill /F /IM "uvicorn.exe" >nul 2>&1
taskkill /F /IM "node.exe" /FI "WINDOWTITLE eq Frontend*" >nul 2>&1
echo [DONE] Application closed.
