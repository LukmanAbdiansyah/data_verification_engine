from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
import asyncio
import json
import logging
import os
from typing import Dict, Any

from dotenv import load_dotenv, dotenv_values
from ..database.engine import get_db, async_session_maker
from ..models.models import ValidationRun, Requirement, RepositoryFile, RequirementResult, CandidateEvidence, AIAssessment, SettingsMetadata
from ..schemas.schemas import RequirementResultSchema, ValidationProgress
from ..services.validation_engine import ValidationEngine
from ..services.decision_engine import get_folder_summary
from ..services.ai_client import AIClient
from .websocket import manager

router = APIRouter()
logger = logging.getLogger(__name__)

val_tasks: Dict[str, asyncio.Event] = {}

async def _background_validation(run_id: str):
    cancel_event = asyncio.Event()
    val_tasks[run_id] = cancel_event
    
    async def progress_cb(progress: Dict):
        await manager.broadcast(run_id, {"type": "validation_progress", "data": progress})
        
    try:
        async with async_session_maker() as db:
            run_stmt = select(ValidationRun).where(ValidationRun.id == run_id)
            run = (await db.execute(run_stmt)).scalar_one_or_none()
            if not run:
                return
                
            run.status = 'validating'
            await db.commit()
            
            req_stmt = select(Requirement).where(Requirement.run_id == run_id)
            reqs = (await db.execute(req_stmt)).scalars().all()
            
            file_stmt = select(RepositoryFile).where(RepositoryFile.run_id == run_id)
            files = (await db.execute(file_stmt)).scalars().all()
            
            req_list = [
                {
                    'id': r.id,
                    'req_id': r.req_id,
                    'progress': r.progress,
                    'formats': json.loads(r.formats_json)
                } for r in reqs
            ]
            
            file_list = [
                {
                    'id': f.id,
                    'full_path': f.full_path,
                    'relative_path': f.relative_path,
                    'filename': f.filename,
                    'extension': f.extension,
                    'size_bytes': f.size_bytes,
                    'modified_time': f.modified_time,
                    'parent_directory': f.parent_directory,
                    'readable': f.readable,
                    'file_type': f.file_type
                } for f in files
            ]
            
            # Load latest settings from .env and SettingsMetadata table
            load_dotenv(override=True)
            env_vals = dotenv_values(".env")
            
            settings_stmt = select(SettingsMetadata)
            s_rows = (await db.execute(settings_stmt)).scalars().all()
            db_settings = {r.key: r.value for r in s_rows}
            
            ai_enabled = db_settings.get('ai_enabled', env_vals.get('AI_ENABLED', os.getenv('AI_ENABLED', 'true'))).lower() == 'true'
            base_url = (env_vals.get('UNSLOTH_BASE_URL') or os.getenv('UNSLOTH_BASE_URL', '')).strip()
            api_key = env_vals.get('UNSLOTH_API_KEY') or os.getenv('UNSLOTH_API_KEY', '')
            model = (env_vals.get('UNSLOTH_MODEL') or os.getenv('UNSLOTH_MODEL', '')).strip()
            timeout = int(env_vals.get('AI_TIMEOUT') or os.getenv('AI_TIMEOUT', 120))
            max_tokens = int(env_vals.get('AI_MAX_TOKENS') or os.getenv('AI_MAX_TOKENS', 4096))
            if max_tokens < 4096:
                max_tokens = 4096
            
            ai_client = None
            if ai_enabled and base_url and model:
                ai_client = AIClient(
                    base_url=base_url,
                    api_key=api_key,
                    model=model,
                    timeout=timeout,
                    max_tokens=max_tokens
                )
            
            engine = ValidationEngine(ai_client=ai_client, ai_enabled=ai_enabled)
            
            results = await engine.run_validation(run_id, req_list, file_list, {'model_name': model}, progress_cb, cancel_event)
            
            if cancel_event.is_set():
                run.status = 'cancelled'
                await db.commit()
                return
            
            # Save results
            await db.execute(delete(RequirementResult).where(RequirementResult.run_id == run_id))
            
            pass_c, partial_c, missing_c, invalid_c, review_c = 0, 0, 0, 0, 0
            
            for res in results:
                req_id = res['requirement']['id']
                overall = res['overall_status']
                
                if overall == 'PASS': pass_c += 1
                elif overall == 'PARTIAL': partial_c += 1
                elif overall == 'MISSING': missing_c += 1
                elif overall == 'INVALID': invalid_c += 1
                elif overall == 'REVIEW_REQUIRED': review_c += 1
                
                for f_res in res['format_results']:
                    db_res = RequirementResult(
                        run_id=run_id,
                        requirement_id=req_id,
                        format_name=f_res['format_name'],
                        matched_file_id=f_res.get('matched_file_id'),
                        system_status=f_res['system_status'],
                        final_status=f_res['system_status'],
                        evidence_level=f_res['evidence_level'],
                        technical_validation_json=json.dumps(f_res.get('technical_validation')) if f_res.get('technical_validation') else None,
                        ai_assessment_json=json.dumps(f_res.get('ai_assessment')) if f_res.get('ai_assessment') else None,
                        evidence_data_json=json.dumps(f_res.get('candidates', []))
                    )
                    db.add(db_res)
            
            run.status = 'completed'
            run.pass_count = pass_c
            run.partial_count = partial_c
            run.missing_count = missing_c
            run.invalid_count = invalid_c
            run.review_count = review_c
            await db.commit()
            
    except Exception as e:
        logger.error(f"Validation error: {e}")
        async with async_session_maker() as db:
            run_stmt = select(ValidationRun).where(ValidationRun.id == run_id)
            run = (await db.execute(run_stmt)).scalar_one_or_none()
            if run:
                run.status = 'failed'
                await db.commit()
    finally:
        val_tasks.pop(run_id, None)

@router.post("/{run_id}/start")
async def start_validation(run_id: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    if run_id in val_tasks:
        raise HTTPException(status_code=400, detail="Validation is already running for this session.")
        
    stmt = select(ValidationRun).where(ValidationRun.id == run_id)
    run = (await db.execute(stmt)).scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run ID not found. Please confirm your checklist first.")
        
    req_stmt = select(Requirement).where(Requirement.run_id == run_id)
    reqs = (await db.execute(req_stmt)).scalars().all()
    if not reqs:
        raise HTTPException(status_code=400, detail="No requirements found. Please go to the Checklist tab and click 'Confirm Checklist' before validating.")
        
    file_stmt = select(RepositoryFile).where(RepositoryFile.run_id == run_id)
    files = (await db.execute(file_stmt)).scalars().all()
    if not files:
        raise HTTPException(status_code=400, detail="No files found in repository. Please go to the Repository tab and click 'Scan Repository' first.")
        
    background_tasks.add_task(_background_validation, run_id)
    return {"status": "started", "run_id": run_id, "total_requirements": len(reqs), "total_files": len(files)}

@router.get("/{run_id}/status")
async def get_validation_status(run_id: str, db: AsyncSession = Depends(get_db)):
    if run_id in val_tasks:
        return {"status": "validating", "run_id": run_id}
    stmt = select(ValidationRun).where(ValidationRun.id == run_id)
    run = (await db.execute(stmt)).scalar_one_or_none()
    if run:
        return {
            "status": run.status,
            "run_id": run_id,
            "total_requirements": run.total_requirements,
            "pass_count": run.pass_count,
            "partial_count": run.partial_count,
            "missing_count": run.missing_count,
            "invalid_count": run.invalid_count,
            "review_count": run.review_count
        }
    return {"status": "idle", "run_id": run_id}

@router.post("/{run_id}/cancel")
async def cancel_validation(run_id: str):
    if run_id in val_tasks:
        val_tasks[run_id].set()
        return {"status": "cancelling"}
    return {"status": "not_running"}

@router.get("/{run_id}/results")
async def get_results(run_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(RequirementResult, Requirement, RepositoryFile).join(Requirement).outerjoin(RepositoryFile, RequirementResult.matched_file_id == RepositoryFile.id).where(RequirementResult.run_id == run_id)
    result = await db.execute(stmt)
    rows = result.all()
    
    out = []
    for res, req, file in rows:
        cands = json.loads(res.evidence_data_json) if res.evidence_data_json else []
        matched_str = file.filename if file else None
        matched_path = file.relative_path if file else None
        
        if len(cands) > 1:
            paths = [c['relative_path'] for c in cands if c.get('relative_path')]
            fallback = file.parent_directory if file else ''
            common_dir = get_folder_summary(paths, fallback)
            matched_str = f"{len(cands)} files ({common_dir})"
            matched_path = common_dir
            
        out.append({
            "id": res.id,
            "req_id": req.req_id,
            "progress": req.progress,
            "format_name": res.format_name,
            "matched_file": matched_str,
            "matched_file_path": matched_path,
            "system_status": res.system_status,
            "final_status": res.final_status,
            "manual_override": res.manual_override,
            "evidence_level": res.evidence_level,
            "candidates": cands,
            "ai_assessment": json.loads(res.ai_assessment_json) if res.ai_assessment_json else None
        })
    return out

@router.get("/{run_id}/result/{req_id}")
async def get_result_detail(run_id: str, req_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(RequirementResult, Requirement, RepositoryFile).join(Requirement).outerjoin(RepositoryFile, RequirementResult.matched_file_id == RepositoryFile.id).where(RequirementResult.run_id == run_id, Requirement.id == req_id)
    result = await db.execute(stmt)
    rows = result.all()
    if not rows:
        raise HTTPException(status_code=404)
        
    out = []
    for res, req, file in rows:
        cands = json.loads(res.evidence_data_json) if res.evidence_data_json else []
        matched_str = file.filename if file else None
        matched_path = file.relative_path if file else None
        
        if len(cands) > 1:
            paths = [c['relative_path'] for c in cands if c.get('relative_path')]
            fallback = file.parent_directory if file else ''
            common_dir = get_folder_summary(paths, fallback)
            matched_str = f"{len(cands)} files ({common_dir})"
            matched_path = common_dir
            
        out.append({
            "id": res.id,
            "req_id": req.req_id,
            "progress": req.progress,
            "format_name": res.format_name,
            "matched_file": matched_str,
            "matched_file_path": matched_path,
            "system_status": res.system_status,
            "final_status": res.final_status,
            "manual_override": res.manual_override,
            "evidence_level": res.evidence_level,
            "candidates": cands,
            "ai_assessment": json.loads(res.ai_assessment_json) if res.ai_assessment_json else None,
            "reviewer_note": res.reviewer_note,
            "technical_validation": json.loads(res.technical_validation_json) if res.technical_validation_json else None
        })
    return out
