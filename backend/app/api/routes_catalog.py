import os
import json
import asyncio
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from ..services.catalog_generator import (
    list_files_with_paths_and_folders,
    is_segy_file,
    is_las_file,
    generate_seismic_catalog,
    generate_well_catalog,
    path_for_io,
)

logger = logging.getLogger(__name__)
router = APIRouter()


class ScanCatalogFolderRequest(BaseModel):
    folder_path: str
    category: Optional[str] = "seismic"  # 'seismic' or 'well'


class GenerateSeismicCatalogRequest(BaseModel):
    catalog_type: str
    folder_path: str
    params: Dict[str, Any] = {}


class GenerateWellCatalogRequest(BaseModel):
    catalog_type: str
    folder_path: str
    params: Dict[str, Any] = {}


@router.post("/browse-folder")
async def browse_catalog_folder():
    """Open a native Windows directory picker dialog and return the selected folder path."""
    def _open_dialog():
        # First attempt: Tkinter native folder dialog
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            folder = filedialog.askdirectory(title="Pilih Folder Data")
            root.destroy()
            if folder:
                return folder.replace('/', '\\')
        except Exception as e:
            logger.warning(f"Tkinter dialog error: {e}")

        # Second attempt: PowerShell Windows Forms FolderBrowserDialog
        try:
            import subprocess
            ps_cmd = (
                "[System.Reflection.Assembly]::LoadWithPartialName('System.windows.forms') | Out-Null; "
                "$dialog = New-Object System.Windows.Forms.FolderBrowserDialog; "
                "$dialog.Description = 'Pilih Folder Data'; "
                "if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { $dialog.SelectedPath }"
            )
            res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True, timeout=60)
            selected = res.stdout.strip()
            if selected:
                return selected
        except Exception as e:
            logger.warning(f"PowerShell dialog error: {e}")

        return None

    selected_folder = _open_dialog()
    return {"path": selected_folder}


@router.post("/scan-folder")
async def scan_catalog_folder(req: ScanCatalogFolderRequest):
    """Scan the target folder and return file summary, counts, and extensions."""
    if not os.path.isdir(path_for_io(req.folder_path)):
        raise HTTPException(status_code=400, detail="Folder tidak ditemukan.")

    try:
        paths, names, dirs = list_files_with_paths_and_folders(req.folder_path)
        ext_counts: Dict[str, int] = {}
        segy_count = 0
        las_count = 0

        for name in names:
            _, ext = os.path.splitext(name)
            ext_clean = ext.lower()
            ext_counts[ext_clean] = ext_counts.get(ext_clean, 0) + 1
            if is_segy_file(name):
                segy_count += 1
            if is_las_file(name):
                las_count += 1

        return {
            "folder_path": req.folder_path,
            "total_files": len(names),
            "segy_count": segy_count,
            "las_count": las_count,
            "extension_summary": ext_counts,
            "sample_files": names[:15],
        }
    except Exception as e:
        logger.error(f"Error scanning folder {req.folder_path}: {e}")
        raise HTTPException(status_code=500, detail=f"Gagal memindai folder: {str(e)}")


@router.post("/generate/seismic")
async def api_generate_seismic_catalog(req: GenerateSeismicCatalogRequest):
    """Generate Seismic data catalog and export to Excel."""
    if not os.path.isdir(path_for_io(req.folder_path)):
        raise HTTPException(status_code=400, detail="Folder tidak ditemukan.")

    try:
        result = await asyncio.to_thread(
            generate_seismic_catalog,
            catalog_type=req.catalog_type,
            folder_path=req.folder_path,
            params=req.params
        )
        return result
    except Exception as e:
        logger.error(f"Error generating seismic catalog: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Gagal membuat catalog seismik: {str(e)}")


@router.post("/generate/seismic-stream")
async def api_generate_seismic_catalog_stream(req: GenerateSeismicCatalogRequest):
    """Generate Seismic data catalog with real-time NDJSON progress streaming."""
    if not os.path.isdir(path_for_io(req.folder_path)):
        raise HTTPException(status_code=400, detail="Folder tidak ditemukan.")

    loop = asyncio.get_running_loop()
    queue = asyncio.Queue()

    def progress_callback(data):
        if isinstance(data, dict):
            payload = {"type": "progress", **data}
        else:
            payload = {"type": "progress", "percent": data, "message": ""}
        loop.call_soon_threadsafe(queue.put_nowait, payload)

    def run_worker():
        try:
            result = generate_seismic_catalog(
                catalog_type=req.catalog_type,
                folder_path=req.folder_path,
                params=req.params,
                progress_callback=progress_callback
            )
            loop.call_soon_threadsafe(queue.put_nowait, {"type": "complete", "result": result})
        except Exception as e:
            logger.error(f"Error in generate_seismic_catalog stream: {e}", exc_info=True)
            loop.call_soon_threadsafe(queue.put_nowait, {"type": "error", "error": str(e)})

    loop.run_in_executor(None, run_worker)

    async def event_generator():
        while True:
            item = await queue.get()
            try:
                yield json.dumps(item, default=str) + "\n"
            except Exception as json_err:
                logger.error(f"Error serializing stream item: {json_err}", exc_info=True)
                yield json.dumps({"type": "error", "error": f"Gagal serialisasi data katalog: {json_err}"}) + "\n"
                break
            if item.get("type") in ("complete", "error"):
                break

    return StreamingResponse(
        event_generator(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/generate/well")
async def api_generate_well_catalog(req: GenerateWellCatalogRequest):
    """Generate Well data catalog and export to Excel."""
    if not os.path.isdir(path_for_io(req.folder_path)):
        raise HTTPException(status_code=400, detail="Folder tidak ditemukan.")

    try:
        result = await asyncio.to_thread(
            generate_well_catalog,
            catalog_type=req.catalog_type,
            folder_path=req.folder_path,
            params=req.params
        )
        return result
    except Exception as e:
        logger.error(f"Error generating well catalog: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Gagal membuat catalog well: {str(e)}")



@router.post("/generate/well-stream")
async def api_generate_well_catalog_stream(req: GenerateWellCatalogRequest):
    """Generate Well data catalog with real-time NDJSON progress streaming."""
    if not os.path.isdir(path_for_io(req.folder_path)):
        raise HTTPException(status_code=400, detail="Folder tidak ditemukan.")

    loop = asyncio.get_running_loop()
    queue = asyncio.Queue()

    def progress_callback(data):
        if isinstance(data, dict):
            payload = {"type": "progress", **data}
        else:
            payload = {"type": "progress", "percent": data, "message": ""}
        loop.call_soon_threadsafe(queue.put_nowait, payload)

    def run_worker():
        try:
            result = generate_well_catalog(
                catalog_type=req.catalog_type,
                folder_path=req.folder_path,
                params=req.params,
                progress_callback=progress_callback
            )
            loop.call_soon_threadsafe(queue.put_nowait, {"type": "complete", "result": result})
        except Exception as e:
            logger.error(f"Error in generate_well_catalog stream: {e}", exc_info=True)
            loop.call_soon_threadsafe(queue.put_nowait, {"type": "error", "error": str(e)})

    loop.run_in_executor(None, run_worker)

    async def event_generator():
        while True:
            item = await queue.get()
            try:
                yield json.dumps(item, default=str) + "\n"
            except Exception as json_err:
                logger.error(f"Error serializing stream item: {json_err}", exc_info=True)
                yield json.dumps({"type": "error", "error": f"Gagal serialisasi data katalog: {json_err}"}) + "\n"
                break
            if item.get("type") in ("complete", "error"):
                break

    return StreamingResponse(
        event_generator(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/download")
async def download_catalog(file_path: str = Query(..., description="Path to generated Excel file")):
    """Download generated catalog Excel file."""
    norm_path = path_for_io(file_path)
    if not os.path.isfile(norm_path):
        raise HTTPException(status_code=404, detail="File catalog tidak ditemukan.")

    filename = os.path.basename(file_path)
    return FileResponse(
        path=norm_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename
    )
