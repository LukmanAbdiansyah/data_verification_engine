from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
import json
from typing import List

from ..database.engine import get_db
from ..models.models import (
    ValidationRun, Requirement, RepositoryFile, RequirementResult,
    CandidateEvidence, AIAssessment, ManualReview
)
from ..schemas.schemas import RunSummary, ExportRequest
from ..services.export_service import export_xlsx, export_json, export_pdf

router = APIRouter()

@router.get("", response_model=List[RunSummary], include_in_schema=False)
@router.get("/", response_model=List[RunSummary])
async def list_history(db: AsyncSession = Depends(get_db)):
    stmt = select(ValidationRun).order_by(ValidationRun.created_at.desc())
    runs = (await db.execute(stmt)).scalars().all()
    
    return [
        RunSummary(
            run_id=r.id,
            date=r.created_at,
            checklist=r.checklist_filename,
            repository=r.repository_root,
            total=r.total_requirements,
            pass_count=r.pass_count,
            partial_count=r.partial_count,
            missing_count=r.missing_count,
            invalid_count=r.invalid_count,
            review_count=r.review_count,
            model_name=r.model_name,
            status=r.status
        ) for r in runs
    ]

@router.delete("")
@router.delete("/")
async def clear_all_history(db: AsyncSession = Depends(get_db)):
    """Delete all validation runs and associated data."""
    await db.execute(delete(ManualReview))
    await db.execute(delete(CandidateEvidence))
    await db.execute(delete(AIAssessment))
    await db.execute(delete(RequirementResult))
    await db.execute(delete(RepositoryFile))
    await db.execute(delete(Requirement))
    await db.execute(delete(ValidationRun))
    await db.commit()
    return {"status": "all_deleted"}

@router.get("/{run_id}")
async def get_run(run_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(ValidationRun).where(ValidationRun.id == run_id)
    run = (await db.execute(stmt)).scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404)
    return run

@router.delete("/{run_id}")
async def delete_run(run_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a specific validation run and all its related records."""
    # Find all result_ids for this run
    result_ids_stmt = select(RequirementResult.id).where(RequirementResult.run_id == run_id)
    res_ids = (await db.execute(result_ids_stmt)).scalars().all()
    if res_ids:
        await db.execute(delete(ManualReview).where(ManualReview.result_id.in_(res_ids)))
        await db.execute(delete(CandidateEvidence).where(CandidateEvidence.result_id.in_(res_ids)))
        await db.execute(delete(AIAssessment).where(AIAssessment.result_id.in_(res_ids)))
        
    await db.execute(delete(RequirementResult).where(RequirementResult.run_id == run_id))
    await db.execute(delete(RepositoryFile).where(RepositoryFile.run_id == run_id))
    await db.execute(delete(Requirement).where(Requirement.run_id == run_id))
    await db.execute(delete(ValidationRun).where(ValidationRun.id == run_id))
    await db.commit()
    return {"status": "deleted"}

@router.post("/{run_id}/export")
async def export_run(run_id: str, req: ExportRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(ValidationRun).where(ValidationRun.id == run_id)
    run = (await db.execute(stmt)).scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404)
        
    req_stmt = select(Requirement).where(Requirement.run_id == run_id)
    reqs = (await db.execute(req_stmt)).scalars().all()
    
    res_stmt = select(RequirementResult).where(RequirementResult.run_id == run_id)
    results = (await db.execute(res_stmt)).scalars().all()
    
    run_data = {
        'summary': {
            'run_id': run.id,
            'date': run.created_at,
            'checklist': run.checklist_filename,
            'repository': run.repository_root,
            'status': run.status,
            'total': run.total_requirements,
            'pass_count': run.pass_count,
            'partial_count': run.partial_count,
            'missing_count': run.missing_count,
            'invalid_count': run.invalid_count,
            'review_count': run.review_count,
        },
        'requirements': []
    }
    
    res_by_req = {}
    for r in results:
        if r.requirement_id not in res_by_req:
            res_by_req[r.requirement_id] = []
        res_by_req[r.requirement_id].append(r)
        
    for r in reqs:
        req_results = res_by_req.get(r.id, [])
        status = req_results[0].final_status if req_results else 'MISSING' # simplification
        run_data['requirements'].append({
            'req_id': r.req_id,
            'progress': r.progress,
            'formats': json.loads(r.formats_json),
            'status': status,
            'validation_note': r.validation_note
        })
    
    if req.format == 'xlsx':
        data = export_xlsx(run_data)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ext = "xlsx"
    elif req.format == 'pdf':
        data = export_pdf(run_data)
        media_type = "application/pdf"
        ext = "pdf"
    else:
        data = export_json(run_data)
        media_type = "application/json"
        ext = "json"
        
    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename=report_{run_id}.{ext}"}
    )
