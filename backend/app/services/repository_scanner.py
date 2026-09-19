import os
import time
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Callable
from ..schemas.schemas import ScanProgress, FileInfo

class RepositoryScanner:
    async def scan(self, root_path: str, run_id: str, progress_callback: Callable = None, cancel_event: asyncio.Event = None) -> List[Dict[str, Any]]:
        root = Path(root_path)
        if not root.exists():
            raise ValueError(f"Path does not exist: {root_path}")
        files = []
        files_count = 0
        folders_count = 0
        file_type_counts = {}
        start_time = time.time()
        
        for dirpath, dirnames, filenames in os.walk(root_path):
            if cancel_event and cancel_event.is_set():
                break
            folders_count += 1
            for fname in filenames:
                if cancel_event and cancel_event.is_set():
                    break
                full_path = os.path.join(dirpath, fname)
                try:
                    stat = os.stat(full_path)
                    ext = os.path.splitext(fname)[1].lower()
                    rel_path = os.path.relpath(full_path, root_path)
                    file_info = {
                        'full_path': full_path,
                        'relative_path': rel_path,
                        'filename': fname,
                        'extension': ext,
                        'size_bytes': stat.st_size,
                        'modified_time': time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(stat.st_mtime)),
                        'parent_directory': os.path.basename(dirpath),
                        'readable': os.access(full_path, os.R_OK),
                        'file_type': None
                    }
                    files.append(file_info)
                    files_count += 1
                    ext_key = ext if ext else 'no_ext'
                    file_type_counts[ext_key] = file_type_counts.get(ext_key, 0) + 1
                    
                    if progress_callback and (files_count % 20 == 0 or files_count <= 10):
                        await progress_callback(ScanProgress(
                            files_scanned=files_count,
                            folders_scanned=folders_count,
                            current_folder=os.path.relpath(dirpath, root_path),
                            elapsed_seconds=round(time.time() - start_time, 1),
                            file_type_counts=file_type_counts,
                            status='scanning'
                        ))
                except (PermissionError, OSError):
                    file_info = {
                        'full_path': full_path,
                        'relative_path': os.path.relpath(full_path, root_path),
                        'filename': fname,
                        'extension': os.path.splitext(fname)[1].lower(),
                        'size_bytes': 0,
                        'modified_time': '',
                        'parent_directory': os.path.basename(dirpath),
                        'readable': False,
                        'file_type': None
                    }
                    files.append(file_info)
                    files_count += 1
                if files_count % 50 == 0:
                    await asyncio.sleep(0)
        
        if progress_callback:
            await progress_callback(ScanProgress(
                files_scanned=files_count,
                folders_scanned=folders_count,
                current_folder='',
                elapsed_seconds=round(time.time() - start_time, 1),
                file_type_counts=file_type_counts,
                status='completed'
            ))
        return files

class RepositoryCache:
    def check_cache_valid(self, run_id: str, root_path: str, db_files: List) -> bool:
        if not db_files: return False
        try:
            for db_f in db_files[:10]: # Check a sample
                full_path = os.path.join(root_path, db_f.relative_path)
                if not os.path.exists(full_path):
                    return False
                stat = os.stat(full_path)
                if stat.st_size != db_f.size_bytes:
                    return False
            return True
        except Exception:
            return False

    def find_changed_files(self, cached_files: List, current_scan: List) -> List:
        cached_dict = {f.full_path: f for f in cached_files}
        changed = []
        for f in current_scan:
            if f['full_path'] not in cached_dict:
                changed.append(f)
            else:
                cached = cached_dict[f['full_path']]
                if cached.size_bytes != f['size_bytes'] or cached.modified_time != f['modified_time']:
                    changed.append(f)
        return changed
