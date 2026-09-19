import os
import uuid
import logging
from typing import Any
from pathlib import Path
from .errors import VerificationError
from .inventory import FileInventory, scan_inventory, validate_path
from .registry import VerificationToolRegistry
from .session import VerificationSessionStore

logger = logging.getLogger(__name__)

def _integer_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (ValueError, TypeError):
        return default

class VerificationCoordinator:
    def __init__(self, *, registry=None, store=None, scanner=scan_inventory):
        ttl = _integer_env('VERIFICATION_CACHE_TTL_SECONDS', 1800)
        self.registry = registry or VerificationToolRegistry()
        self.store = store or VerificationSessionStore(ttl_seconds=ttl)
        self.scanner = scanner
    
    def run(self, session_id: str | None, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if not session_id:
            session_id = str(uuid.uuid4())
        
        state = self.store.get(session_id)
        canonical = self.registry.canonical_name(tool_name)
        
        # Normalize parameter aliases
        args = dict(arguments)
        if not args.get('folder_path') and args.get('target_folder'):
            args['folder_path'] = args['target_folder']
        if not args.get('file_column') and args.get('file_column_name'):
            args['file_column'] = args['file_column_name']
        if not args.get('search_scope') and 'recursive_per_folder' in args:
            args['search_scope'] = 'recursive_per_folder' if args['recursive_per_folder'] else 'direct_files'
        if not args.get('match_mode'):
            args['match_mode'] = 'any'

        folder_path = str(args.get('folder_path', '')).strip()
        if not folder_path:
            raise VerificationError('MISSING_ARGUMENTS', 'Pilih folder yang akan diperiksa.', field='folder_path')
        
        resolved_folder = validate_path(folder_path, kind='folder')
        
        cached_inventory = None
        if state.inventory:
            try:
                if Path(state.inventory.root_path).resolve() == resolved_folder:
                    cached_inventory = state.inventory
            except Exception:
                pass
        
        inventory = cached_inventory or self.scanner(str(resolved_folder))
        result = self.registry.execute(canonical, args, inventory=inventory)
        
        state.result = result
        state.inventory = inventory
        state.last_tool = canonical
        state.last_args = args
        self.store.save(session_id, state)
        
        result['session_id'] = session_id
        return result
    
    def get_result(self, session_id: str) -> dict[str, Any] | None:
        state = self.store.get(session_id)
        return state.result
