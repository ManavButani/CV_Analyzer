"""Resume Parser Agent - Converts resumes into structured data"""
from schema.resume_screening import StructuredResume
from typing import Tuple
from logic.llm_handler import LLMHandler


async def parse_resume(
    resume_text: str,
    handler: LLMHandler,
    candidate_name: str = None
) -> Tuple[StructuredResume, int]:
    """
    Parse resume and extract structured information.
    
    Returns:
        Tuple of (StructuredResume, status_code)
    """
    try:
        
        system_prompt = """
        Parse the following resume and extract structured information.
        
        Extract:
        1. Candidate Name: Full name of the candidate (if available)
        2. Skills: List all technical and professional skills mentioned
        3. Experience: List all work experiences with:
           - Job title/role
           - Company name
           - Duration (years/months)
           - Description of responsibilities
        4. Total Years of Experience: Calculate total years of professional experience
        5. Projects: List notable projects (if mentioned)
        6. Education: List educational qualifications with:
           - Degree/qualification
           - Institution
           - Year (if mentioned)
        7. Certifications: List any certifications mentioned
        
        Handle missing or messy formatting robustly. If information is not available, 
        use empty lists or null values. Be as comprehensive as possible in extraction.
        """
        
        user_content = resume_text
        if candidate_name:
            user_content = f"Candidate Name (if not in resume): {candidate_name}\n\n{resume_text}"
        
        structured_resume, status = await handler.invoke_structured(
            prompt="Parse this resume:",
            system_prompt=system_prompt,
            response_schema=StructuredResume,
            user_content=user_content
        )
        
        # Ensure raw_text is preserved
        structured_resume.raw_text = resume_text
        if candidate_name and not structured_resume.candidate_name:
            structured_resume.candidate_name = candidate_name
            
        return structured_resume, status
        
    except Exception as e:
        # Return error with minimal structure
        error_resume = StructuredResume(
            candidate_name=candidate_name or "Unknown",
            skills=[],
            experience=[],
            total_years_experience=0.0,
            raw_text=resume_text
        )
        return error_resume, 400
