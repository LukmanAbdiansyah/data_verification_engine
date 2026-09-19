# ============================================================================
# build_python_embed.ps1
# Downloads Python 3.11 Embedded and installs all backend dependencies into it
# This creates a portable Python distribution for the installer
# ============================================================================

$ErrorActionPreference = "Stop"

$PYTHON_VERSION  = "3.11.9"
$PYTHON_SHORT    = "311"
$EMBED_ZIP_URL   = "https://www.python.org/ftp/python/$PYTHON_VERSION/python-$PYTHON_VERSION-embed-amd64.zip"
$GET_PIP_URL     = "https://bootstrap.pypa.io/get-pip.py"

$ROOT_DIR        = Split-Path -Parent $MyInvocation.MyCommand.Definition
$BUILD_DIR       = Join-Path $ROOT_DIR "build"
$PYTHON_DIR      = Join-Path $BUILD_DIR "python-embed"
$PYTHON_EXE      = Join-Path $PYTHON_DIR "python.exe"
$PTH_FILE        = Join-Path $PYTHON_DIR "python${PYTHON_SHORT}._pth"
$ZIP_FILE        = Join-Path $BUILD_DIR "python-embed.zip"
$GET_PIP_FILE    = Join-Path $BUILD_DIR "get-pip.py"
$REQUIREMENTS    = Join-Path (Join-Path $ROOT_DIR "backend") "requirements.txt"

Write-Host ""
Write-Host "  ======================================================" -ForegroundColor Cyan
Write-Host "   Python Embedded Builder" -ForegroundColor Cyan
Write-Host "   Python $PYTHON_VERSION (amd64) + pip + requirements" -ForegroundColor Cyan
Write-Host "  ======================================================" -ForegroundColor Cyan
Write-Host ""

# --- Step 0: Create build directory ---
if (!(Test-Path $BUILD_DIR)) {
    New-Item -ItemType Directory -Path $BUILD_DIR -Force | Out-Null
}

# --- Step 1: Download Python Embedded ---
if (Test-Path $PYTHON_DIR) {
    Write-Host "[SKIP] Python embedded already exists at: $PYTHON_DIR" -ForegroundColor Yellow
    Write-Host "       Delete 'build/python-embed' to force re-download." -ForegroundColor Yellow
} else {
    Write-Host "[1/5] Downloading Python $PYTHON_VERSION embedded..." -ForegroundColor Green
    if (!(Test-Path $ZIP_FILE)) {
        Invoke-WebRequest -Uri $EMBED_ZIP_URL -OutFile $ZIP_FILE -UseBasicParsing
        Write-Host "       Downloaded: $ZIP_FILE"
    } else {
        Write-Host "       Using cached zip: $ZIP_FILE"
    }

    Write-Host "[2/5] Extracting Python embedded..." -ForegroundColor Green
    Expand-Archive -Path $ZIP_FILE -DestinationPath $PYTHON_DIR -Force
    Write-Host "       Extracted to: $PYTHON_DIR"
}

# --- Step 2: Enable import site (required for pip/packages to work) ---
Write-Host "[3/5] Configuring python${PYTHON_SHORT}._pth for site-packages..." -ForegroundColor Green
if (Test-Path $PTH_FILE) {
    $pthContent = Get-Content $PTH_FILE -Raw
    if ($pthContent -match "^#\s*import site") {
        # Uncomment 'import site'
        $pthContent = $pthContent -replace "^#\s*import site", "import site"
        Set-Content -Path $PTH_FILE -Value $pthContent -NoNewline
        Write-Host "       Enabled 'import site' in ._pth file"
    } elseif ($pthContent -match "^import site") {
        Write-Host "       'import site' already enabled"
    } else {
        Add-Content -Path $PTH_FILE -Value "`nimport site"
        Write-Host "       Added 'import site' to ._pth file"
    }
} else {
    Write-Host "       WARNING: ._pth file not found at $PTH_FILE" -ForegroundColor Red
}

# --- Step 3: Install pip ---
Write-Host "[4/5] Installing pip into embedded Python..." -ForegroundColor Green
if (!(Test-Path $GET_PIP_FILE)) {
    Invoke-WebRequest -Uri $GET_PIP_URL -OutFile $GET_PIP_FILE -UseBasicParsing
}

# Check if pip already installed (temporarily relax error handling for this check)
$ErrorActionPreference = "SilentlyContinue"
$pipCheck = & $PYTHON_EXE -m pip --version 2>&1
$pipExitCode = $LASTEXITCODE
$ErrorActionPreference = "Stop"

if ($pipExitCode -eq 0) {
    Write-Host "       pip already installed: $pipCheck"
} else {
    Write-Host "       Installing pip via get-pip.py..."
    $ErrorActionPreference = "SilentlyContinue"
    & $PYTHON_EXE $GET_PIP_FILE --no-warn-script-location 2>&1 | ForEach-Object {
        Write-Host "       $_"
    }
    $pipInstallExit = $LASTEXITCODE
    $ErrorActionPreference = "Stop"

    if ($pipInstallExit -ne 0) {
        Write-Host "ERROR: Failed to install pip!" -ForegroundColor Red
        exit 1
    }
    Write-Host "       pip installed successfully"
}

# --- Step 4: Install all backend requirements ---
Write-Host "[5/5] Installing backend requirements..." -ForegroundColor Green
Write-Host "       Source: $REQUIREMENTS"
Write-Host "       This may take several minutes..."
Write-Host ""

$ErrorActionPreference = "SilentlyContinue"
& $PYTHON_EXE -m pip install -r $REQUIREMENTS --no-warn-script-location --no-cache-dir 2>&1 | ForEach-Object {
    if ($_ -match "^(Successfully|Installing|Collecting|Downloading|Building|ERROR|WARNING)") {
        Write-Host "       $_"
    }
}
$reqExitCode = $LASTEXITCODE
$ErrorActionPreference = "Stop"

if ($reqExitCode -ne 0) {
    Write-Host ""
    Write-Host "ERROR: Failed to install some requirements!" -ForegroundColor Red
    Write-Host "       Check the output above for details." -ForegroundColor Red
    exit 1
}

# --- Step 5: Verify ---
Write-Host ""
Write-Host "  Verifying installation..." -ForegroundColor Cyan
$verifyScript = @"
import sys
print(f'  Python: {sys.version}')
try:
    import fastapi; print(f'  FastAPI: {fastapi.__version__}')
except: print('  FastAPI: FAILED')
try:
    import uvicorn; print(f'  Uvicorn: {uvicorn.__version__}')
except: print('  Uvicorn: FAILED')
try:
    import pandas; print(f'  Pandas: {pandas.__version__}')
except: print('  Pandas: FAILED')
try:
    import sqlalchemy; print(f'  SQLAlchemy: {sqlalchemy.__version__}')
except: print('  SQLAlchemy: FAILED')
try:
    import openpyxl; print(f'  Openpyxl: {openpyxl.__version__}')
except: print('  Openpyxl: FAILED')
print('  All core imports OK!')
"@
$ErrorActionPreference = "SilentlyContinue"
& $PYTHON_EXE -c $verifyScript 2>&1 | ForEach-Object { Write-Host $_ }
$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "  ======================================================" -ForegroundColor Green
Write-Host "   Python Embedded build COMPLETE!" -ForegroundColor Green
Write-Host "   Location: $PYTHON_DIR" -ForegroundColor Green

# Calculate size
$size = (Get-ChildItem -Path $PYTHON_DIR -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
Write-Host "   Size: $([math]::Round($size, 1)) MB" -ForegroundColor Green
Write-Host "  ======================================================" -ForegroundColor Green
Write-Host ""
