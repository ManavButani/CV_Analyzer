from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.security import OAuth2PasswordBearer
from typing import List, Optional
import base64
from sqlalchemy.orm import Session
from schema.user import User
from schema.resume_screening import (
    ResumeScreeningRequest, ResumeScreeningResponse,
    JDInput, ResumeInput, FileFormat
)
from logic.auth import get_current_active_user
from logic.resume_screening import orchestrate_resume_screening
from logic.utils import get_traceback_string
from core.database import get_db

router = APIRouter()


@router.post("/screen/", response_model=ResumeScreeningResponse)
async def screen_resumes(
    request: ResumeScreeningRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Main endpoint for resume screening.
    
    Accepts:
    - JD (as text or file)
    - Multiple resumes (as text or files)
    - Optional scoring weights
    
    Returns ranked candidates with explanations.
    Uses LLM provider configured in database.
    """
    try:
        response, status_code = await orchestrate_resume_screening(request, db)
        
        if status_code != 200:
            error_msg = response.summary.common_gaps_observed[0] if response and response.summary.common_gaps_observed else 'Unknown error'
            raise HTTPException(
                status_code=status_code,
                detail=f"Resume screening failed: {error_msg}"
            )
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        traceback_str = get_traceback_string()
        raise HTTPException(
            status_code=500,
            detail=f"Error: {str(e)}\nTraceback:\n{traceback_str}"
        )


@router.post("/screen/files/", response_model=ResumeScreeningResponse)
async def screen_resumes_files(
    jd_file: UploadFile = File(...),
    resume_files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Alternative endpoint that accepts file uploads directly.
    
    Files are converted to base64 and processed.
    """
    try:
        # Read JD file
        jd_content = await jd_file.read()
        jd_base64 = base64.b64encode(jd_content).decode('utf-8')
        jd_format = jd_file.filename.split('.')[-1].lower() if jd_file.filename else "txt"
        
        # Read resume files
        resume_inputs = []
        for resume_file in resume_files:
            resume_content = await resume_file.read()
            resume_base64 = base64.b64encode(resume_content).decode('utf-8')
            resume_format = resume_file.filename.split('.')[-1].lower() if resume_file.filename else "txt"
            
            # Map format to enum
            format_map = {
                "pdf": FileFormat.PDF,
                "docx": FileFormat.DOCX,
                "txt": FileFormat.TXT
            }
            
            resume_input = ResumeInput(
                resume_file=resume_base64,
                file_format=format_map.get(resume_format, FileFormat.TXT),
                candidate_name=resume_file.filename
            )
            resume_inputs.append(resume_input)
        
        # Create request
        format_map = {
            "pdf": FileFormat.PDF,
            "docx": FileFormat.DOCX,
            "txt": FileFormat.TXT
        }
        
        jd_input = JDInput(
            jd_file=jd_base64,
            file_format=format_map.get(jd_format, FileFormat.TXT)
        )
        
        request = ResumeScreeningRequest(
            jd=jd_input,
            resumes=resume_inputs
        )
        
        # Process
        response, status_code = await orchestrate_resume_screening(request, db)
        
        if status_code != 200:
            error_msg = response.summary.common_gaps_observed[0] if response and response.summary.common_gaps_observed else 'Unknown error'
            raise HTTPException(
                status_code=status_code,
                detail=f"Resume screening failed: {error_msg}"
            )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        traceback_str = get_traceback_string()
        raise HTTPException(
            status_code=500,
            detail=f"Error processing files: {str(e)}\nTraceback:\n{traceback_str}"
        )
