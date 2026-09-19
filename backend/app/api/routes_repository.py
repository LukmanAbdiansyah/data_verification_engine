from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
import asyncio
import uuid
import subprocess
import time
from typing import Dict, Any, Optional
import logging

from ..database.engine import get_db, async_session_maker
from ..models.models import ValidationRun, RepositoryFile
from ..schemas.schemas import RepositoryScanRequest, ScanProgress, FileInfo
from ..services.repository_scanner import RepositoryScanner
from .websocket import manager

router = APIRouter()
logger = logging.getLogger(__name__)

scan_tasks: Dict[str, asyncio.Event] = {}


async def _execute_scan(run_id: str, path: str, db: AsyncSession) -> Dict[str, Any]:
    scanner = RepositoryScanner()
    cancel_event = asyncio.Event()
    scan_tasks[run_id] = cancel_event
    start_time = time.time()

    async def progress_cb(progress: ScanProgress):
        try:
            await manager.broadcast(run_id, {"type": "scan_progress", "data": progress.model_dump()})
        except Exception:
            pass

    try:
        files = await scanner.scan(path, run_id, progress_cb, cancel_event)
        if cancel_event.is_set():
            return {"status": "cancelled", "run_id": run_id, "files_scanned": 0}

        # Update run repository_root
        stmt = select(ValidationRun).where(ValidationRun.id == run_id)
        run = (await db.execute(stmt)).scalar_one_or_none()
        if run:
            run.repository_root = path
            run.status = 'scanned'

        # Clear any prior files for this run
        await db.execute(delete(RepositoryFile).where(RepositoryFile.run_id == run_id))

        # Bulk insert scanned files
        db_files = [
            RepositoryFile(
                run_id=run_id,
                full_path=f['full_path'],
                relative_path=f['relative_path'],
                filename=f['filename'],
                extension=f['extension'],
                size_bytes=f['size_bytes'],
                modified_time=f['modified_time'],
                parent_directory=f['parent_directory'],
                readable=f['readable'],
                file_type=f.get('file_type')
            ) for f in files
        ]
        db.add_all(db_files)
        await db.commit()

        # Calculate extension counts
        file_type_counts: Dict[str, int] = {}
        unique_folders = set()
        for f in files:
            ext = f['extension'] or 'no_ext'
            file_type_counts[ext] = file_type_counts.get(ext, 0) + 1
            if f.get('parent_directory'):
                unique_folders.add(f['parent_directory'])

        elapsed = round(time.time() - start_time, 2)
        summary = {
            "status": "completed",
            "run_id": run_id,
            "files_scanned": len(files),
            "folders_scanned": len(unique_folders),
            "elapsed_seconds": elapsed,
            "file_type_counts": file_type_counts
        }

        # Broadcast completion to websocket clients
        try:
            await manager.broadcast(run_id, {"type": "scan_completed", "data": summary})
        except Exception:
            pass

        return summary

    except Exception as e:
        logger.error(f"Scan failed: {e}")
        try:
            await manager.broadcast(run_id, {"type": "scan_error", "data": str(e)})
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Scan error: {str(e)}")
    finally:
        scan_tasks.pop(run_id, None)


@router.post("/browse-folder")
async def browse_folder():
    """Open a native Windows directory picker dialog and return the selected folder path."""
    def _open_dialog():
        # First attempt: Tkinter native folder dialog
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            folder = filedialog.askdirectory(title="Select Deliverable Repository")
            root.destroy()
            if folder:
                return folder.replace('/', '\\')
        except Exception as e:
            logger.warning(f"Tkinter dialog error: {e}")

        # Second attempt: PowerShell Windows Forms FolderBrowserDialog
        try:
            ps_cmd = (
                "[System.Reflection.Assembly]::LoadWithPartialName('System.windows.forms') | Out-Null; "
                "$dialog = New-Object System.Windows.Forms.FolderBrowserDialog; "
                "$dialog.Description = 'Select Deliverable Repository Folder'; "
                "if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { $dialog.SelectedPath }"
            )
            res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True, timeout=60)
            selected = res.stdout.strip()
            if selected:
                return selected
        except Exception as e:
            logger.error(f"PowerShell folder dialog error: {e}")

        return None

    selected_path = await asyncio.to_thread(_open_dialog)
    return {"path": selected_path}


@router.post("/scan")
async def start_scan_general(request: RepositoryScanRequest, db: AsyncSession = Depends(get_db)):
    """Start scanning a repository. If no run_id is supplied, automatically generates one."""
    run_id = request.run_id
    if not run_id:
        new_run = ValidationRun(
            id=str(uuid.uuid4()),
            repository_root=request.path,
            status='scanning'
        )
        db.add(new_run)
        await db.commit()
        run_id = new_run.id

    if run_id in scan_tasks:
        raise HTTPException(status_code=400, detail="Scan already in progress for this run")

    return await _execute_scan(run_id, request.path, db)


@router.post("/{run_id}/scan")
async def start_scan(run_id: str, request: RepositoryScanRequest, db: AsyncSession = Depends(get_db)):
    if run_id in scan_tasks:
        raise HTTPException(status_code=400, detail="Scan already in progress")
        
    return await _execute_scan(run_id, request.path, db)


@router.get("/scan/{run_id}/status")
@router.get("/{run_id}/scan/status")
async def get_scan_status(run_id: str, db: AsyncSession = Depends(get_db)):
    if run_id in scan_tasks:
        return {"status": "scanning", "run_id": run_id}
    
    stmt = select(RepositoryFile).where(RepositoryFile.run_id == run_id)
    files = (await db.execute(stmt)).scalars().all()
    if files:
        file_type_counts: Dict[str, int] = {}
        unique_folders = set()
        for f in files:
            ext = f.extension or 'no_ext'
            file_type_counts[ext] = file_type_counts.get(ext, 0) + 1
            if f.parent_directory:
                unique_folders.add(f.parent_directory)
        return {
            "status": "completed",
            "run_id": run_id,
            "files_scanned": len(files),
            "folders_scanned": len(unique_folders),
            "elapsed_seconds": 0.0,
            "file_type_counts": file_type_counts
        }
    return {"status": "idle", "run_id": run_id, "files_scanned": 0, "folders_scanned": 0, "file_type_counts": {}}


@router.post("/{run_id}/cancel")
async def cancel_scan(run_id: str):
    if run_id in scan_tasks:
        scan_tasks[run_id].set()
        return {"status": "cancelling"}
    return {"status": "not_running"}


@router.get("/{run_id}/files")
async def get_files(run_id: str, page: int = 1, per_page: int = 100, db: AsyncSession = Depends(get_db)):
    offset = (page - 1) * per_page
    stmt = select(RepositoryFile).where(RepositoryFile.run_id == run_id).offset(offset).limit(per_page)
    result = await db.execute(stmt)
    files = result.scalars().all()
    
    return [
        FileInfo(
            id=f.id,
            full_path=f.full_path,
            relative_path=f.relative_path,
            filename=f.filename,
            extension=f.extension,
            size_bytes=f.size_bytes,
            modified_time=f.modified_time,
            parent_directory=f.parent_directory,
            readable=f.readable,
            file_type=f.file_type
        )
        for f in files
    ]
