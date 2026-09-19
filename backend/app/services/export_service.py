import json
import io
import openpyxl
from typing import Dict, Any

def export_xlsx(run_data: Dict[str, Any]) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "SUMMARY"
    
    summary = run_data.get('summary', {})
    ws.append(["Run ID", summary.get('run_id')])
    ws.append(["Date", summary.get('date')])
    ws.append(["Checklist", summary.get('checklist')])
    ws.append(["Repository", summary.get('repository')])
    ws.append(["Status", summary.get('status')])
    ws.append([])
    ws.append(["Metrics"])
    ws.append(["Total Requirements", summary.get('total')])
    ws.append(["Pass", summary.get('pass_count')])
    ws.append(["Partial", summary.get('partial_count')])
    ws.append(["Missing", summary.get('missing_count')])
    ws.append(["Invalid", summary.get('invalid_count')])
    ws.append(["Review Required", summary.get('review_count')])
    
    ws_results = wb.create_sheet("CHECKLIST_RESULTS")
    ws_results.append(["ID", "Requirement", "Formats", "Status", "Notes"])
    for req in run_data.get('requirements', []):
        ws_results.append([req.get('req_id'), req.get('progress'), ", ".join(req.get('formats', [])), req.get('status'), req.get('validation_note')])
    
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()

def export_json(run_data: Dict[str, Any]) -> bytes:
    return json.dumps(run_data, indent=2).encode('utf-8')

def export_pdf(run_data: Dict[str, Any]) -> bytes:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=letter)
    width, height = letter
    
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "Deliverable Verification Report")
    
    c.setFont("Helvetica", 12)
    summary = run_data.get('summary', {})
    y = height - 80
    c.drawString(50, y, f"Run ID: {summary.get('run_id')}")
    c.drawString(50, y-20, f"Date: {summary.get('date')}")
    c.drawString(50, y-40, f"Status: {summary.get('status')}")
    
    c.drawString(50, y-80, f"Total Requirements: {summary.get('total')}")
    c.drawString(50, y-100, f"Pass: {summary.get('pass_count')}")
    c.drawString(50, y-120, f"Missing: {summary.get('missing_count')}")
    
    c.save()
    return out.getvalue()
