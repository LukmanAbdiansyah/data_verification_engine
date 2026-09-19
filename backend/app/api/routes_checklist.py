from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
import os
import aiofiles

from ..database.engine import get_db
from ..models.models import ValidationRun, Requirement
from ..schemas.schemas import ChecklistUploadResponse, ChecklistConfirmRequest
from ..services.deliverable_parser import parse_xlsx, parse_csv, parse_paste
from ..services.requirement_normalizer import normalize_requirements
import json

router = APIRouter()

@router.post("/upload", response_model=ChecklistUploadResponse)
async def upload_checklist(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    os.makedirs("temp", exist_ok=True)
    temp_path = f"temp/{uuid.uuid4()}_{file.filename}"
    
    async with aiofiles.open(temp_path, 'wb') as out_file:
        content = await file.read()
        await out_file.write(content)
        
    try:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext in ['.xlsx', '.xls']:
            rows, mapping, headers = parse_xlsx(temp_path)
        elif ext == '.csv':
            rows, mapping, headers = parse_csv(temp_path)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")
            
        run_id = str(uuid.uuid4())
        
        return ChecklistUploadResponse(
            rows=rows,
            detected_columns=mapping,
            mapping_required=mapping['progress'] is None or mapping['format'] is None,
            column_options=headers,
            run_id=run_id
        )
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

from pydantic import BaseModel
from sqlalchemy import select, delete

class PasteRequest(BaseModel):
    text: str

@router.post("/paste", response_model=ChecklistUploadResponse)
async def paste_checklist(request: PasteRequest, db: AsyncSession = Depends(get_db)):
    rows, mapping, headers = parse_paste(request.text)
    run_id = str(uuid.uuid4())
    
    return ChecklistUploadResponse(
        rows=rows,
        detected_columns=mapping,
        mapping_required=mapping['progress'] is None or mapping['format'] is None,
        column_options=headers,
        run_id=run_id
    )

@router.post("/{run_id}/confirm")
async def confirm_checklist(run_id: str, request: ChecklistConfirmRequest, db: AsyncSession = Depends(get_db)):
    reqs_dicts = [req.model_dump() for req in request.requirements]
    normalized = normalize_requirements(reqs_dicts)
    
    stmt = select(ValidationRun).where(ValidationRun.id == run_id)
    run = (await db.execute(stmt)).scalar_one_or_none()
    if not run:
        run = ValidationRun(id=run_id, total_requirements=len(normalized))
        db.add(run)
    else:
        run.total_requirements = len(normalized)
        
    await db.execute(delete(Requirement).where(Requirement.run_id == run_id))
    
    for req in normalized:
        db_req = Requirement(
            run_id=run_id,
            req_id=req['req_id'],
            source_row=req['source_row'],
            progress=req['progress'],
            formats_json=json.dumps(req['formats']),
            validation_note=req.get('validation_note')
        )
        db.add(db_req)
        
    await db.commit()
    return {"status": "success", "run_id": run_id}

@router.get("/{run_id}")
async def get_checklist(run_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Requirement).where(Requirement.run_id == run_id)
    result = await db.execute(stmt)
    reqs = result.scalars().all()
    
    return [
        {
            "id": r.id,
            "req_id": r.req_id,
            "source_row": r.source_row,
            "progress": r.progress,
            "formats": json.loads(r.formats_json),
            "validation_note": r.validation_note
        }
        for r in reqs
    ]
