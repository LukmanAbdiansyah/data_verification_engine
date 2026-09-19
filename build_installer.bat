@echo off
title Seismic Checker - Build Installer
color 0B
echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║  SEISMIC DELIVERABLE AI CHECKER                         ║
echo  ║  Building Windows Installer (.exe)                      ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

:: ── Check Prerequisites ──
echo [CHECK] Checking build prerequisites...
echo.

where node >nul 2>&1
if errorlevel 1 (
    echo  [X] Node.js NOT FOUND - Required for building
    echo      Download: https://nodejs.org/
    pause
    exit /b 1
) else (
    for /f "tokens=*" %%i in ('node --version 2^>^&1') do echo  [OK] Node.js %%i
)

where npm >nul 2>&1
if errorlevel 1 (
    echo  [X] npm NOT FOUND
    pause
    exit /b 1
) else (
    for /f "tokens=*" %%i in ('npm --version 2^>^&1') do echo  [OK] npm %%i
)

echo.
echo ══════════════════════════════════════════════════════════
echo.

:: ── Step 1: Build Python Embedded ──
echo [1/5] Building Python Embedded distribution...
echo       (downloading Python 3.11 + installing all pip packages)
echo.
powershell -ExecutionPolicy Bypass -File "%~dp0build_python_embed.ps1"
if errorlevel 1 (
    echo.
    echo [ERROR] Python embedded build failed!
    pause
    exit /b 1
)

:: Verify python-embed exists
if not exist "build\python-embed\python.exe" (
    echo [ERROR] build\python-embed\python.exe not found!
    echo         Python embedded build may have failed.
    pause
    exit /b 1
)
echo [OK] Python embedded ready.
echo.

:: ── Step 2: Install Node dependencies ──
echo [2/5] Installing Node.js dependencies...
if not exist "node_modules" (
    call npm install
) else (
    echo       Already installed - skipping
)

if not exist "frontend\node_modules" (
    cd frontend
    call npm install
    cd ..
) else (
    echo       Frontend deps already installed - skipping
)
echo [OK] Node dependencies ready.
echo.

:: ── Step 3: Build Frontend ──
echo [3/5] Building frontend (React + Vite)...
cd frontend
call npm run build
if errorlevel 1 (
    echo [ERROR] Frontend build failed!
    cd ..
    pause
    exit /b 1
)
cd ..

if not exist "frontend\dist\index.html" (
    echo [ERROR] frontend\dist\index.html not found!
    echo         Frontend build may have failed.
    pause
    exit /b 1
)
echo [OK] Frontend build ready.
echo.

:: ── Step 4: Compile Electron TypeScript ──
echo [4/5] Compiling Electron TypeScript...
call npx tsc -p tsconfig.electron.json
if errorlevel 1 (
    echo [ERROR] Electron TypeScript compilation failed!
    pause
    exit /b 1
)

if not exist "dist-electron\main.js" (
    echo [ERROR] dist-electron\main.js not found!
    pause
    exit /b 1
)
echo [OK] Electron compiled.
echo.

:: ── Step 5: Build Installer with electron-builder ──
echo [5/5] Building NSIS installer with electron-builder...
echo       This may take a few minutes...
echo.
call npx electron-builder --win --x64
if errorlevel 1 (
    echo.
    echo [ERROR] electron-builder failed!
    echo         Check the output above for details.
    pause
    exit /b 1
)

echo.
echo ══════════════════════════════════════════════════════════
echo.

:: ── Check output ──
if exist "release\*.exe" (
    echo  ╔══════════════════════════════════════════════════════════╗
    echo  ║  BUILD SUCCESSFUL!                                      ║
    echo  ║                                                         ║
    echo  ║  Installer created in:                                  ║
    echo  ║  release\                                               ║
    echo  ╚══════════════════════════════════════════════════════════╝
    echo.
    echo  Files in release folder:
    dir /b release\*.exe 2>nul
    echo.
    echo  You can now distribute this installer to other PCs!
    echo  No Python or Node.js needed on target machines.
) else (
    echo  [WARNING] No .exe found in release\ folder.
    echo            Build may have completed with warnings.
)

echo.
pause
