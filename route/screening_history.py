"""API routes for accessing screening request history"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from core.database import get_db
from logic.auth import get_current_active_user
from logic.screening_storage import get_screening_record, get_all_screening_records
from schema.user import User
from const.route import DS

router = APIRouter()


@router.get("/history/{request_id}")
async def get_screening_history(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get screening request details by request_id"""
    record = get_screening_record(db, request_id)
    
    if not record:
        raise HTTPException(status_code=404, detail="Screening request not found")
    
    return {
        "request_id": record.request_id,
        "timestamp": record.timestamp.isoformat() if record.timestamp else None,
        "model_provider": record.model_provider,
        "model_name": record.model_name,
        "jd_file_path": record.jd_file_path,
        "resume_files_paths": record.resume_files_paths,
        "jd_text_preview": record.jd_text_preview,
        "resume_count": record.resume_count,
        "total_resumes_processed": record.total_resumes_processed,
        "total_candidates_ranked": record.total_candidates_ranked,
        "processing_status": record.processing_status,
        "error_message": record.error_message,
        "reasoning_json": record.reasoning_json,
        "output_json": record.output_json,
        "intermediate_outputs": record.intermediate_outputs
    }


@router.get("/history/")
async def list_screening_history(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all screening requests with pagination"""
    records = get_all_screening_records(db, limit=limit, offset=offset)
    
    return [
        {
            "request_id": record.request_id,
            "timestamp": record.timestamp.isoformat() if record.timestamp else None,
            "model_provider": record.model_provider,
            "model_name": record.model_name,
            "resume_count": record.resume_count,
            "total_resumes_processed": record.total_resumes_processed,
            "total_candidates_ranked": record.total_candidates_ranked,
            "processing_status": record.processing_status,
            "jd_text_preview": record.jd_text_preview
        }
        for record in records
    ]
