@echo off
title Seismic Checker - Frontend Only
color 0D
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║  FRONTEND SERVER (Vite + React)          ║
echo  ║  http://localhost:5176                   ║
echo  ╚══════════════════════════════════════════╝
echo.

cd /d "%~dp0frontend"

:: Install if needed
if not exist "node_modules" (
    echo [SETUP] Installing frontend dependencies...
    call npm install
)

echo [START] Starting Vite dev server...
echo.
call npm run dev
pause
