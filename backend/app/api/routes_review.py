from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from ..database.engine import get_db
from ..models.models import RequirementResult, ManualReview
from ..schemas.schemas import ManualReviewRequest

router = APIRouter()

@router.post("/{result_id}")
async def submit_review(result_id: int, request: ManualReviewRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(RequirementResult).where(RequirementResult.id == result_id)
    res = (await db.execute(stmt)).scalar_one_or_none()
    if not res:
        raise HTTPException(status_code=404, detail="Result not found")
        
    prev = res.final_status
    res.final_status = request.new_status
    res.manual_override = True
    res.reviewer_note = request.reviewer_note
    res.review_timestamp = datetime.now(timezone.utc).isoformat()
    
    review = ManualReview(
        result_id=result_id,
        previous_status=prev,
        new_status=request.new_status,
        reviewer_note=request.reviewer_note
    )
    db.add(review)
    
    # Also need to update the run summary stats, but we can do that dynamically on read or do a full recompute.
    
    await db.commit()
    return {"status": "success"}
