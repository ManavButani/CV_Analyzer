"""Database model for storing resume screening requests and results"""
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.sql import func
from core.database import Base
import uuid


class ScreeningRequestInDB(Base):
    """Store complete screening request with input, output, and reasoning"""
    __tablename__ = "screening_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String, unique=True, index=True, nullable=False, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Model information
    model_provider = Column(String, nullable=False)  # e.g., "openai", "gemini", "grok"
    model_name = Column(String, nullable=True)  # e.g., "gpt-4o", "gemini-pro"
    
    # Input files storage paths
    jd_file_path = Column(String, nullable=True)  # Path to JD file in uploads folder
    resume_files_paths = Column(JSON, nullable=True)  # List of resume file paths
    
    # Input data (text content)
    jd_text_preview = Column(Text, nullable=True)  # First 500 chars of JD
    resume_count = Column(Integer, default=0)
    
    # Output and reasoning
    reasoning_json = Column(JSON, nullable=True)  # Complete reasoning log
    output_json = Column(JSON, nullable=True)  # Complete response JSON
    intermediate_outputs = Column(JSON, nullable=True)  # Intermediate outputs
    
    # Metadata
    total_resumes_processed = Column(Integer, default=0)
    total_candidates_ranked = Column(Integer, default=0)
    processing_status = Column(String, default="completed")  # completed, failed, processing
    error_message = Column(Text, nullable=True)
