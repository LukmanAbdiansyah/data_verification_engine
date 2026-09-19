import os
from typing import Dict, Any

def inspect_docx(file_path: str) -> Dict[str, Any]:
    try:
        from docx import Document
        doc = Document(file_path)
        title = doc.core_properties.title or ''
        headings = [p.text for p in doc.paragraphs if p.style.name.startswith('Heading')][:10]
        first_paragraphs = [p.text for p in doc.paragraphs if p.text.strip()][:20]
        content_preview = ' '.join(first_paragraphs)[:500]
        return {'title': title, 'headings': headings, 'content_preview': content_preview, 'type': 'DOCX'}
    except Exception as e:
        return {'type': 'DOCX', 'error': str(e)}

def inspect_xlsx_file(file_path: str) -> Dict[str, Any]:
    try:
        import openpyxl
        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        sheet_names = wb.sheetnames
        first_rows = []
        ws = wb.active
        for i, row in enumerate(ws.iter_rows(values_only=True, max_row=5)):
            first_rows.append([str(c) if c else '' for c in row])
        wb.close()
        return {'sheet_names': sheet_names, 'first_rows': first_rows, 'type': 'XLSX'}
    except Exception as e:
        return {'type': 'XLSX', 'error': str(e)}

def inspect_pdf(file_path: str) -> Dict[str, Any]:
    try:
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            metadata = pdf.metadata or {}
            title = metadata.get('Title', '') or ''
            pages_text = []
            for page in pdf.pages[:2]:
                text = page.extract_text() or ''
                pages_text.append(text[:500])
        return {'title': title, 'metadata': {k: str(v) for k, v in metadata.items()}, 'pages_text': pages_text, 'type': 'PDF'}
    except Exception as e:
        return {'type': 'PDF', 'error': str(e)}

def inspect_office_file(file_path: str) -> Dict[str, Any]:
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == '.docx': return inspect_docx(file_path)
        elif ext == '.xlsx': return inspect_xlsx_file(file_path)
        elif ext == '.pdf': return inspect_pdf(file_path)
        elif ext in ('.doc', '.xls', '.ppt', '.pptx'):
            return {'type': ext.upper().lstrip('.'), 'note': 'Limited inspection for legacy format'}
        else:
            return {'type': 'UNKNOWN', 'note': 'Unsupported office format'}
    except Exception as e:
        return {'type': 'ERROR', 'error': str(e)}
