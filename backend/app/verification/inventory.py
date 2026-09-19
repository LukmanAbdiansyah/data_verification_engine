from __future__ import annotations
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from .errors import VerificationError

VERIFICATION_MAX_FILES = int(os.getenv('VERIFICATION_MAX_FILES', '50000'))

@dataclass(frozen=True)
class InventoryFile:
    name: str
    relative_path: str

@dataclass
class FileInventory:
    root_path: str
    files: list[InventoryFile] = field(default_factory=list)
    subfolders: list[str] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    scanned_at: str = field(default_factory=lambda: time.strftime('%Y-%m-%dT%H:%M:%S'))

def validate_path(path_str: str, kind: str) -> Path:
    try:
        resolved = Path(path_str).resolve()
    except Exception as e:
        raise VerificationError('INVALID_PATH', f'Path tidak valid: {str(e)}', field='path')
    
    if not resolved.exists():
        raise VerificationError('PATH_NOT_FOUND', f'Path tidak ditemukan: {path_str}', field='path')
    
    if kind == 'folder' and not resolved.is_dir():
        raise VerificationError('NOT_A_FOLDER', f'Bukan sebuah folder: {path_str}', field='path')
    elif kind == 'metadata' and not resolved.is_file():
        raise VerificationError('NOT_A_FILE', f'Bukan sebuah file: {path_str}', field='path')
        
    return resolved

def scan_inventory(folder_path: str) -> FileInventory:
    try:
        resolved_root = validate_path(folder_path, kind='folder')
    except VerificationError:
        raise
        
    inventory = FileInventory(root_path=str(resolved_root))
    
    try:
        for entry in os.scandir(resolved_root):
            if entry.is_dir(follow_symlinks=False):
                inventory.subfolders.append(entry.name)
    except PermissionError as e:
        inventory.warnings.append({'type': 'permission_error', 'message': str(e)})
        return inventory
        
    for root, dirs, files in os.walk(resolved_root, followlinks=False):
        try:
            rel_root = Path(root).relative_to(resolved_root).as_posix()
            if rel_root == ".":
                rel_root = ""
        except ValueError:
            continue
            
        for file in files:
            if len(inventory.files) >= VERIFICATION_MAX_FILES:
                inventory.warnings.append({
                    'type': 'max_files_exceeded', 
                    'message': f'Batas maksimal {VERIFICATION_MAX_FILES} file tercapai.'
                })
                return inventory
                
            rel_path = f"{rel_root}/{file}" if rel_root else file
            inventory.files.append(InventoryFile(name=file, relative_path=rel_path))
            
    return inventory
