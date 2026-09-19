from typing import Set

EXTENSION_MAP = {
    '.sgy': 'SEG-Y', '.segy': 'SEG-Y', '.sgd': 'SEG-D', '.segd': 'SEG-D',
    '.txt': 'ASCII', '.asc': 'ASCII', '.dat': 'ASCII', '.ascii': 'ASCII',
    '.csv': 'CSV',
    '.pdf': 'PDF',
    '.tif': 'TIFF', '.tiff': 'TIFF',
    '.doc': 'DOC', '.docx': 'DOCX',
    '.xls': 'XLS', '.xlsx': 'XLSX',
    '.ppt': 'PPT', '.pptx': 'PPTX',
    '.jpg': 'IMAGE', '.jpeg': 'IMAGE', '.png': 'IMAGE', '.bmp': 'IMAGE',
}

FORMAT_EXTENSIONS = {
    'SEG-Y': {'.sgy', '.segy'},
    'SEG-D': {'.sgd', '.segd'},
    'ASCII': {'.txt', '.asc', '.dat', '.ascii'},
    'CSV': {'.csv'},
    'PDF': {'.pdf'},
    'TIFF': {'.tif', '.tiff'},
    'DOC': {'.doc'}, 'DOCX': {'.docx'},
    'XLS': {'.xls'}, 'XLSX': {'.xlsx'},
    'PPT': {'.ppt'}, 'PPTX': {'.pptx'},
    'MS-OFFICE': {'.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'},
    'UKOOA': {'.txt', '.asc', '.dat', '.p698', '.p190', '.p294'},
    'UKOOA P6/98': {'.txt', '.asc', '.dat', '.p698'},
    'P1/90': {'.txt', '.asc', '.dat', '.p190'},
    'P2/94': {'.txt', '.asc', '.dat', '.p294'},
    'TXT': {'.txt'},
}

def classify_file(extension: str) -> str:
    return EXTENSION_MAP.get(extension.lower(), 'OTHER')

def get_format_extensions(format_name: str) -> Set[str]:
    return FORMAT_EXTENSIONS.get(format_name, set())

def is_format_match(file_extension: str, required_format: str) -> bool:
    exts = get_format_extensions(required_format)
    if not exts:
        return True # If format is unknown, we can't filter by extension effectively
    return file_extension.lower() in exts
