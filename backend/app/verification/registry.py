from __future__ import annotations
from typing import Any
from .errors import VerificationError
from .inventory import FileInventory
from . import tools

_TOOL_SPECS = {
    'verify_catalog': {
        'required': ['folder_path'],
        'optional': ['metadata_path', 'metadata_paths', 'sheet_name', 'file_column', 'case_sensitive'],
        'func': tools.verify_catalog,
    },
    'search_files_by_keywords': {
        'required': ['folder_path', 'keywords'],
        'optional': ['match_mode', 'recursive', 'case_sensitive'],
        'func': tools.search_files_by_keywords,
    },
    'verify_keyword_coverage': {
        'required': ['folder_path', 'keywords'],
        'optional': ['match_mode', 'search_scope', 'case_sensitive'],
        'func': tools.verify_keyword_coverage,
    },
}

class VerificationToolRegistry:
    def canonical_name(self, name: str) -> str:
        clean_name = str(name).strip().lower()
        if clean_name not in _TOOL_SPECS:
            raise VerificationError('UNKNOWN_TOOL', f'Alat verifikasi tidak dikenal: {name}', field='tool')
        return clean_name
        
    def execute(self, tool_name: str, arguments: dict[str, Any], *, inventory: FileInventory | None = None) -> dict[str, Any]:
        canonical = self.canonical_name(tool_name)
        spec = _TOOL_SPECS[canonical]
        
        if canonical == 'verify_catalog':
            if not arguments.get('metadata_path') and not arguments.get('metadata_paths'):
                raise VerificationError('MISSING_ARGUMENT', 'Pilih minimal satu file metadata Excel.', field='metadata_path')

        for req in spec['required']:
            if req not in arguments:
                raise VerificationError('MISSING_ARGUMENT', f'Argumen wajib tidak ditemukan: {req}', field=req)
                
        func = spec['func']
        
        kwargs = {k: v for k, v in arguments.items() if k in spec['required'] or k in spec['optional']}
        if inventory is not None:
            kwargs['inventory'] = inventory
            
        return func(**kwargs)
