"""Storage logic for screening requests - files and database"""
import os
import uuid
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from model.screening_request import ScreeningRequestInDB
from schema.resume_screening import ResumeScreeningResponse
from logic.llm_handler import LLMHandler


UPLOADS_DIR = "uploads"
JD_SUBDIR = "jd"
RESUME_SUBDIR = "resumes"


def ensure_uploads_directory():
    """Ensure uploads directory structure exists"""
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    os.makedirs(os.path.join(UPLOADS_DIR, JD_SUBDIR), exist_ok=True)
    os.makedirs(os.path.join(UPLOADS_DIR, RESUME_SUBDIR), exist_ok=True)


def save_file_to_uploads(content: bytes, filename: str, subdirectory: str) -> str:
    """
    Save file to uploads folder
    
    Args:
        content: File content as bytes
        filename: Original filename
        subdirectory: Subdirectory within uploads (jd or resumes)
    
    Returns:
        Relative path to saved file
    """
    ensure_uploads_directory()
    
    # Generate unique filename to avoid conflicts
    file_ext = os.path.splitext(filename)[1] if filename else ".txt"
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    
    file_path = os.path.join(UPLOADS_DIR, subdirectory, unique_filename)
    
    with open(file_path, "wb") as f:
        f.write(content)
    
    return file_path


def save_text_to_file(text: str, subdirectory: str, extension: str = ".txt") -> str:
    """
    Save text content to file in uploads folder
    
    Args:
        text: Text content
        subdirectory: Subdirectory within uploads
        extension: File extension
    
    Returns:
        Relative path to saved file
    """
    ensure_uploads_directory()
    
    unique_filename = f"{uuid.uuid4()}{extension}"
    file_path = os.path.join(UPLOADS_DIR, subdirectory, unique_filename)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(text)
    
    return file_path


def create_screening_record(
    db: Session,
    request_id: str,
    handler: LLMHandler,
    jd_file_path: Optional[str] = None,
    resume_file_paths: Optional[List[str]] = None,
    resume_count: int = 0
) -> Optional[ScreeningRequestInDB]:
    """Create a new screening request record"""
    
    try:
        provider_info = handler.get_provider_info()
        
        db_record = ScreeningRequestInDB(
            request_id=request_id,
            model_provider=provider_info.get("provider", "unknown"),
            model_name=provider_info.get("model", "unknown"),
            jd_file_path=jd_file_path,
            resume_files_paths=resume_file_paths or [],
            resume_count=resume_count,
            processing_status="processing"
        )
        
        db.add(db_record)
        db.commit()
        db.refresh(db_record)
        
        return db_record
    except Exception as e:
        # Return None if creation fails, don't break the main flow
        return None


def update_screening_record(
    db: Session,
    request_id: str,
    response: ResumeScreeningResponse,
    reasoning_log: List[Dict[str, Any]],
    intermediate_outputs: Dict[str, Any],
    status: str = "completed",
    error_message: Optional[str] = None
) -> ScreeningRequestInDB:
    """Update screening request record with results"""
    
    db_record = db.query(ScreeningRequestInDB).filter(
        ScreeningRequestInDB.request_id == request_id
    ).first()
    
    if not db_record:
        raise ValueError(f"Screening request {request_id} not found")
    
    # Convert response to JSON
    response_dict = response.model_dump() if hasattr(response, 'model_dump') else response.dict()
    
    # Update record
    db_record.reasoning_json = reasoning_log
    db_record.output_json = response_dict
    db_record.intermediate_outputs = intermediate_outputs
    db_record.total_resumes_processed = response.processing_metadata.get("total_resumes_processed", 0) if response.processing_metadata else 0
    db_record.total_candidates_ranked = response.processing_metadata.get("total_candidates_ranked", 0) if response.processing_metadata else 0
    db_record.processing_status = status
    db_record.error_message = error_message
    
    db.commit()
    db.refresh(db_record)
    
    return db_record


def get_screening_record(db: Session, request_id: str) -> Optional[ScreeningRequestInDB]:
    """Get screening request record by request_id"""
    return db.query(ScreeningRequestInDB).filter(
        ScreeningRequestInDB.request_id == request_id
    ).first()


def get_all_screening_records(
    db: Session,
    limit: int = 100,
    offset: int = 0
) -> List[ScreeningRequestInDB]:
    """Get all screening records with pagination"""
    return db.query(ScreeningRequestInDB).order_by(
        ScreeningRequestInDB.timestamp.desc()
    ).offset(offset).limit(limit).all()
