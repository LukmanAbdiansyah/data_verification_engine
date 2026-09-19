# DATA VERIFICATOR

**Data Verificator** is an enterprise-grade Windows desktop application designed to verify the completeness of data deliverables against user-provided checklists. Built on a *rule-first, evidence-based, conservative, and auditable* approach.

---

## 1. Product Overview & Purpose

Data Verificator checks whether a data repository (local drive / network share / NAS) contains all deliverable items listed in the user's checklist.

- **Authoritative Source of Truth:** The user's deliverable checklist table.
- **Validated Columns:**
  1. `PROGRESS` (Deliverable Name)
  2. `FORMAT` (Expected File Format, e.g. `SEG-Y`, `ASCII`, `MS-Office`, `PDF`, `LAS`)
- **Core Principles:**
  - **Rule-First & Evidence-Based:** Deterministic technical format validation is performed first using file structure analysis.
  - **AI-Assisted:** AI (LLM via Unsloth/Tailscale) acts only as a semantic verification layer when identification is ambiguous or requires text content reasoning.
  - **NO Fuzzy Matching:** Does not use Levenshtein, RapidFuzz, or filename similarity thresholds to automatically produce a PASS status.
  - **Conservative Decision Making:** Supported statuses: `PASS`, `PARTIAL`, `MISSING`, `INVALID`, `REVIEW REQUIRED`. False positives are prevented by requiring both structural and semantic evidence.

---

## 2. Application Architecture

```
                       User Deliverable Table (XLSX / CSV / Paste)
                                          ↓
                              Extract PROGRESS + FORMAT
                                          ↓
                               Checklist Normalization
                                          ↓
                               Native Folder Selection
                                          ↓
                             Recursive Scanner & Cache
                                          ↓
                            Deterministic Classification
                                          ↓
              Technical Format Validation (SEG-Y, ASCII, Office, PDF, LAS)
                                          ↓
                              Content / Header Evidence
                                          ↓
                      AI Semantic Verification (Unsloth via Tailscale)
                                          ↓
                                   Decision Engine
                     (PASS / PARTIAL / MISSING / INVALID / REVIEW)
                                          ↓
                           Review Dashboard & Export (XLSX/PDF)
```

### Technology Stack
- **Frontend:** React + TypeScript + Vite + Tailwind CSS + Lucide React + TanStack Table + Zustand
  - Default Port: `http://localhost:5176`
- **Desktop Shell:** Electron with secure preload IPC bridge (`contextIsolation: true`, `nodeIntegration: false`)
- **Backend:** Python + FastAPI + SQLAlchemy + SQLite
  - Default Port: `http://localhost:8005` (API docs: `http://localhost:8005/docs`)
- **Inference Server:** Private Unsloth OpenAI-compatible endpoint via Tailscale

---

## 3. System Requirements

### A. For End-Users (via Installer)

| Requirement | Details |
|-------------|---------|
| **Operating System** | Windows 10 / 11 (64-bit) |
| **RAM** | Minimum 4 GB |
| **Disk Space** | ~500 MB free space |
| **Network** | Active Tailscale connection *(optional, only required for AI integration)* |

> **Note:** Python and Node.js do **NOT** need to be installed. All dependencies are bundled in the installer.

### B. For Developers (Development Mode)

| Requirement | Details |
|-------------|---------|
| **Operating System** | Windows 10 / 11 (64-bit) |
| **Python** | Version 3.11 or later (must be in `PATH`) |
| **Node.js** | Version 18 or later (with `npm`) |
| **Network** | Active Tailscale connection *(optional)* |

---

## 4. Installation & Distribution (End-User)

### A. Installing from Installer

1. Obtain the file `Seismic Deliverable AI Checker Setup x.x.x.exe` (~258 MB)
2. Double-click the installer file
3. If **Windows SmartScreen** appears (*"Windows protected your PC"*), click **More info** → **Run anyway**
4. Choose the installation location (default is fine) → click **Install**
5. Once complete, launch the application from the **Desktop shortcut** or **Start Menu**

### B. Distributing to Other PCs

Simply copy the **single installer `.exe` file** via:
- USB Flash Drive
- Network Share / Shared Folder
- Google Drive / OneDrive
- Direct LAN file transfer

### C. Uninstalling

Use **Add or Remove Programs** in Windows Settings, or run `Uninstall Seismic Deliverable AI Checker.exe` from the installation folder.

---

## 5. Development Mode (For Developers)

The application includes one-click `.bat` scripts for development:

### A. First-Time Setup
Double-click:
```bat
SETUP.bat
```
This script will:
1. Check for Python, Node.js, and npm.
2. Create a Python virtual environment (`backend\venv`).
3. Install all backend dependencies (`requirements.txt`).
4. Install frontend and Electron dependencies (`npm install`).

---

### B. Running in Web Mode (Browser)
Double-click:
```bat
START_APP.bat
```
- Starts the FastAPI Backend on **`http://localhost:8005`**
- Starts the Vite Frontend on **`http://localhost:5176`**
- Automatically opens the default browser to `http://localhost:5176`.

---

### C. Running in Desktop Mode (Electron)
Double-click:
```bat
START_ELECTRON.bat
```
- Starts backend and frontend in the background.
- Compiles Electron TypeScript and opens a native Windows desktop application window.

---

### D. Running Components Individually (Manual)
- **Backend Only:**
  ```bat
  START_BACKEND.bat
  ```
  or:
  ```powershell
  cd backend
  ..\backend\venv\Scripts\activate.bat
  python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8005
  ```

- **Frontend Only:**
  ```bat
  START_FRONTEND.bat
  ```
  or:
  ```powershell
  cd frontend
  npm run dev
  ```

- **Running Unit & Integration Tests:**
  ```bat
  RUN_TESTS.bat
  ```

- **Creating a Desktop Shortcut:**
  ```bat
  CREATE_DESKTOP_SHORTCUT.bat
  ```

---

## 6. AI Configuration (Unsloth via Tailscale)

Open the **Settings** page in the application:

1. **AI Enabled:** Toggle `Yes/No`.
2. **Unsloth Base URL:**
   - Enter the Tailscale endpoint URL, for example:
     `http://100.x.x.x:8000/v1` or `http://myserver.tailnet-name.ts.net:8000/v1`
   - *Note:* The endpoint is assumed to be OpenAI-compatible (`POST {BASE_URL}/chat/completions`). If the Base URL already ends with `/v1`, the backend automatically prevents path duplication.
3. **API Key:** Enter the authentication token (protected by password masking with Show/Hide toggle). The key is never stored in logs or audit files.
4. **Model Name:** Enter the model name deployed on the Unsloth server (e.g. `Qwen/Qwen2.5-Coder-32B-Instruct`).
5. **Additional Parameters:**
   - Timeout: `120` seconds
   - Max Tokens: `1000`
   - Temperature: `0` (recommended for deterministic output)
   - Max Concurrent Requests: `2`
6. **Test Connection:** Click **Test Connection** to verify connectivity, authentication, and model readiness. Latency will be displayed.

> **Network/AI Failure Note:** If AI Unsloth is offline or unreachable, the application **will not crash**. Deterministic technical checks continue to run normally, and items requiring semantic reasoning will be assigned status `REVIEW REQUIRED` with the note `AI SERVICE UNAVAILABLE`.

---

## 7. Format Validation Details

### SEG-Y Files
The application reads SEG-Y binary and textual headers efficiently without reading the entire trace data volume:
- **Textual Header (3200 bytes):** Auto-detects EBCDIC vs ASCII encoding, decoded into 40 lines × 80 characters.
- **Binary Header (400 bytes):** Extracts sample interval, samples per trace, and sample format code.
- **Contradiction Detection:** If a filename indicates `PSTM` (Pre-Stack Time Migration) but the internal text header indicates `PSDM` (Pre-Stack Depth Migration), the system assigns `REVIEW REQUIRED (CONFLICTING EVIDENCE)`.

### Other Supported Formats
- **MS-Office** (`.xlsx`, `.docx`, `.pptx`) — Validates Office Open XML structure
- **PDF** — Extracts text content for semantic matching
- **ASCII / Text** — Content-based classification
- **LAS** (Log ASCII Standard) — Well log data validation

---

## 8. Build Installer (Production Packaging)

To create a self-contained Windows `.exe` installer (includes Python + all dependencies):

### A. One-Click Build
```bat
build_installer.bat
```

This script automatically runs:
1. **Download & setup Python 3.11 Embedded** + install all pip packages (done once, cached in `build/`)
2. **Build frontend** (React + Vite → static files)
3. **Compile Electron** TypeScript
4. **Create NSIS installer** via electron-builder

### B. Manual Build (Step by Step)
```powershell
# 1. Build Python Embedded (skip if build/python-embed already exists)
powershell -ExecutionPolicy Bypass -File build_python_embed.ps1

# 2. Build frontend
cd frontend && npm run build && cd ..

# 3. Compile Electron TypeScript
npx tsc -p tsconfig.electron.json

# 4. Build installer
npx electron-builder --win --x64
```

### C. Output
```
release/
├── Seismic Deliverable AI Checker Setup x.x.x.exe   ← Installer (~258 MB)
├── win-unpacked/                                      ← Portable version (no install needed)
└── ...
```

### D. What's Included in the Installer

| Component | Description |
|-----------|-------------|
| **Electron Runtime** | Chromium shell for the desktop window |
| **Frontend Build** | React/Vite static files (HTML, CSS, JS) |
| **Backend Source** | FastAPI app (without `.env`, database, or tests) |
| **Python 3.11 Embedded** | Portable Python distribution from python.org + 80+ pip packages |

### E. Updating the Version

Before rebuilding, update the version in `package.json`:
```json
"version": "1.1.0"
```
The installer filename will automatically follow: `Seismic Deliverable AI Checker Setup 1.1.0.exe`

---

## 9. Data & Log Storage Locations

### Development Mode
- **SQLite Database:** `backend/seismic_checker.db` (auto-created on first startup).
- **Application Log:** `backend/logs/seismic_checker.log` (rotating file handler, no secrets/API keys).

### Production Mode (Installer)
- **SQLite Database:** `<install_location>/resources/backend/seismic_checker.db`
- **Application Log:** `<install_location>/resources/backend/logs/seismic_checker.log`
- **AI Configuration:** `<install_location>/resources/backend/.env`

> The **Open Logs Folder** button is available directly on the **Settings** page.

---

## 10. Troubleshooting

### General
1. **Port Conflict:**
   - If port `8005` or `5176` is occupied by another application, ensure there are no zombie uvicorn or node processes. Use `taskkill /F /IM uvicorn.exe` or change the port in `package.json`, `START_*.bat`, and `frontend/vite.config.ts`.
2. **CORS Error:**
   - The FastAPI backend is configured with CORS middleware to allow requests from all local origins.
3. **SEG-Y File Too Small:**
   - Files smaller than 3600 bytes are automatically flagged as `INVALID` because they do not meet the minimum SEG-Y header standard.

### Installer / Production
4. **Windows SmartScreen Warning:**
   - This is normal because the installer is not signed with a paid code-signing certificate. Click **More info** → **Run anyway**.
5. **Blank White Screen After Install:**
   - Ensure you are using the latest installer version. Older versions may have a production mode detection bug.
6. **Backend Not Starting (Application Unresponsive):**
   - Check if port `8005` is blocked by a firewall or antivirus.
   - Try running `Seismic Deliverable AI Checker.exe` directly from the installation folder, then open DevTools (Ctrl+Shift+I) → Console to view error logs.
7. **Installer Build Failed (DNS Error):**
   - If `electron-builder` fails to download NSIS tools, ensure a stable internet connection and that `release-assets.githubusercontent.com` is reachable. Retry `build_installer.bat`.

---

## 11. Project Structure

```
delivirable_verification/
├── backend/                    # Python FastAPI backend
│   ├── app/                    #   Application code (API, models, services, verification)
│   ├── tests/                  #   Unit & integration tests
│   ├── requirements.txt        #   Python dependencies
│   ├── .env                    #   AI configuration (excluded from Git/installer)
│   └── .env.example            #   Configuration template
├── frontend/                   # React + TypeScript frontend
│   ├── src/                    #   Source code (components, hooks, services)
│   └── dist/                   #   Build output (auto-generated)
├── electron/                   # Electron desktop shell
│   ├── main.ts                 #   Main process (backend launcher, window management)
│   ├── preload.ts              #   Preload script (secure IPC bridge)
│   └── ipc/handlers.ts         #   IPC handler registrations
├── dist-electron/              # Compiled Electron JS (auto-generated)
├── build/                      # Build artifacts (auto-generated)
│   └── python-embed/           #   Python 3.11 Embedded + pip packages
├── release/                    # Installer output (auto-generated)
├── build_installer.bat         # ⭐ One-click installer build
├── build_python_embed.ps1      # Python Embedded build script
├── SETUP.bat                   # Setup development environment
├── START_APP.bat               # Run in web mode (browser)
├── START_ELECTRON.bat          # Run in desktop mode (Electron)
├── START_BACKEND.bat           # Run backend only
├── START_FRONTEND.bat          # Run frontend only
├── RUN_TESTS.bat               # Run tests
├── package.json                # Node.js + electron-builder configuration
└── tsconfig.electron.json      # TypeScript config for Electron
```
