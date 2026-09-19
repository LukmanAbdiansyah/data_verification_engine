import { app, BrowserWindow, ipcMain, dialog, shell } from 'electron';
import * as path from 'path';
import { spawn, ChildProcess } from 'child_process';
import * as http from 'http';
import * as fs from 'fs';

let mainWindow: BrowserWindow | null = null;
let backendProcess: ChildProcess | null = null;

const isDev = !app.isPackaged;

// ── Logging helper ──
function log(msg: string) {
  const ts = new Date().toISOString();
  console.log(`[${ts}] ${msg}`);
}

// ── Health-check: wait for backend to be ready ──
function waitForBackend(url: string, timeoutMs: number = 30000): Promise<boolean> {
  return new Promise((resolve) => {
    const start = Date.now();

    const check = () => {
      if (Date.now() - start > timeoutMs) {
        log(`Backend health-check timed out after ${timeoutMs}ms`);
        resolve(false);
        return;
      }

      http
        .get(url, (res) => {
          if (res.statusCode && res.statusCode >= 200 && res.statusCode < 500) {
            log('Backend is ready!');
            resolve(true);
          } else {
            setTimeout(check, 500);
          }
        })
        .on('error', () => {
          setTimeout(check, 500);
        });
    };

    check();
  });
}

// ── Create main window ──
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  if (isDev) {
    mainWindow.loadURL('http://localhost:5176');
    mainWindow.webContents.openDevTools();
    mainWindow.show();
  } else {
    mainWindow.loadFile(path.join(__dirname, '../frontend/dist/index.html'));
    mainWindow.once('ready-to-show', () => {
      mainWindow?.show();
    });
  }
}

// ── Setup .env for production ──
function setupProductionEnv() {
  const backendPath = path.join(process.resourcesPath, 'backend');
  const envPath = path.join(backendPath, '.env');
  const envExamplePath = path.join(backendPath, '.env.example');

  // Create .env from .env.example if it doesn't exist
  if (!fs.existsSync(envPath) && fs.existsSync(envExamplePath)) {
    try {
      fs.copyFileSync(envExamplePath, envPath);
      log('Created .env from .env.example');
    } catch (err) {
      log(`Warning: Could not create .env: ${err}`);
    }
  }

  // Ensure logs directory exists
  const logsPath = path.join(backendPath, 'logs');
  if (!fs.existsSync(logsPath)) {
    try {
      fs.mkdirSync(logsPath, { recursive: true });
      log('Created logs directory');
    } catch (err) {
      log(`Warning: Could not create logs directory: ${err}`);
    }
  }
}

// ── Start backend server ──
function startBackend() {
  if (isDev) {
    log('Dev mode: expecting FastAPI backend on http://localhost:8005');
    return;
  }

  setupProductionEnv();

  const backendPath = path.join(process.resourcesPath, 'backend');
  const pythonExe = path.join(process.resourcesPath, 'python', 'python.exe');

  log(`Starting backend...`);
  log(`  Python: ${pythonExe}`);
  log(`  Backend: ${backendPath}`);

  if (!fs.existsSync(pythonExe)) {
    log(`ERROR: Python executable not found at: ${pythonExe}`);
    dialog.showErrorBox(
      'Backend Error',
      `Python executable not found at:\n${pythonExe}\n\nThe application may not have been installed correctly.`
    );
    return;
  }

  backendProcess = spawn(
    pythonExe,
    ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8005'],
    {
      cwd: backendPath,
      stdio: 'pipe',
      windowsHide: true,
      env: {
        ...process.env,
        PYTHONPATH: backendPath,
        PYTHONNOUSERSITE: '1',
        PYTHONDONTWRITEBYTECODE: '1',
      },
    }
  );

  backendProcess.stdout?.on('data', (data: Buffer) => {
    log(`[Backend stdout] ${data.toString().trim()}`);
  });

  backendProcess.stderr?.on('data', (data: Buffer) => {
    log(`[Backend stderr] ${data.toString().trim()}`);
  });

  backendProcess.on('error', (err: Error) => {
    log(`Backend process error: ${err.message}`);
    dialog.showErrorBox(
      'Backend Error',
      `Failed to start backend server:\n${err.message}`
    );
  });

  backendProcess.on('exit', (code: number | null) => {
    log(`Backend process exited with code: ${code}`);
    backendProcess = null;
  });
}

// ── Graceful shutdown ──
function stopBackend() {
  if (!backendProcess) return;

  log('Stopping backend...');

  try {
    // On Windows, we need to kill the process tree
    if (process.platform === 'win32' && backendProcess.pid) {
      spawn('taskkill', ['/pid', backendProcess.pid.toString(), '/f', '/t'], {
        windowsHide: true,
      });
    } else {
      backendProcess.kill('SIGTERM');
      // Force kill after 5 seconds
      setTimeout(() => {
        if (backendProcess) {
          backendProcess.kill('SIGKILL');
        }
      }, 5000);
    }
  } catch (err) {
    log(`Error stopping backend: ${err}`);
  }

  backendProcess = null;
}

// ── App lifecycle ──
app.whenReady().then(async () => {
  startBackend();

  if (!isDev) {
    // Wait for backend to be ready before showing the window
    log('Waiting for backend to start...');
    const ready = await waitForBackend('http://127.0.0.1:8005/docs', 30000);
    if (!ready) {
      log('WARNING: Backend may not be fully ready yet, showing window anyway');
    }
  }

  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  stopBackend();
});

app.on('quit', () => {
  stopBackend();
});

import './ipc/handlers';
