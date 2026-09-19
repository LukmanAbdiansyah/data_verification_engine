import logging
from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

_coordinator = None

def set_coordinator(coordinator):
    global _coordinator
    _coordinator = coordinator

class VerificationRunRequest(BaseModel):
    session_id: str | None = None
    tool: str
    arguments: dict[str, Any] = {}

@router.post('/run')
def run_verification(request: VerificationRunRequest) -> dict:
    from ..verification.errors import VerificationError
    if _coordinator is None:
        raise HTTPException(status_code=500, detail='Verification engine not initialized')
    try:
        return _coordinator.run(request.session_id, request.tool, request.arguments)
    except VerificationError as exc:
        raise HTTPException(status_code=400, detail=exc.to_dict()) from exc

@router.get('/result/{session_id}')
def get_result(session_id: str) -> dict:
    if _coordinator is None:
        raise HTTPException(status_code=500, detail='Verification engine not initialized')
    result = _coordinator.get_result(session_id)
    if result is None:
        raise HTTPException(status_code=404, detail='No result found for this session')
    return result

@router.post('/browse')
def browse_folder():
    import threading
    result = {'path': None}
    def _pick():
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            path = filedialog.askdirectory(title='Select Folder for Verification')
            root.destroy()
            if path:
                result['path'] = path.replace('/', '\\')
        except Exception:
            pass
    t = threading.Thread(target=_pick)
    t.start()
    t.join(timeout=120)
    return result

@router.post('/browse-file')
def browse_file():
    import threading
    result = {'path': None, 'paths': []}
    def _pick():
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            paths = filedialog.askopenfilenames(
                title='Select Metadata Excel File(s)',
                filetypes=[('Excel files', '*.xlsx;*.xls'), ('All files', '*.*')]
            )
            root.destroy()
            if paths:
                normalized = [p.replace('/', '\\') for p in paths]
                result['paths'] = normalized
                result['path'] = normalized[0]
        except Exception:
            pass
    t = threading.Thread(target=_pick)
    t.start()
    t.join(timeout=120)
    return result

