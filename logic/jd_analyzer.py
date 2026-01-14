"""JD Analyzer Agent - Extracts structured information from Job Description"""
from schema.resume_screening import StructuredJD
from typing import Tuple
from logic.llm_handler import LLMHandler


async def analyze_jd(
    jd_text: str,
    handler: LLMHandler
) -> Tuple[StructuredJD, int]:
    """
    Analyze Job Description and extract structured information.
    
    Returns:
        Tuple of (StructuredJD, status_code)
    """
    try:
        
        system_prompt = """
        Analyze the following Job Description and extract structured information.
        
        Extract:
        1. Role Title: The job title/position name
        2. Role Summary: A brief summary of the role
        3. Mandatory Skills: List of skills that are required (must-have)
        4. Preferred Skills: List of skills that are nice-to-have (optional)
        5. Experience Requirements: 
           - Minimum years of experience required
           - Domain/industry experience needed
           - Any specific experience thresholds
        6. Role Seniority: Classify as "Junior", "Mid-level", "Senior", "Lead", or "Executive"
        7. Education Requirements: Required degrees, certifications (if mentioned)
        8. Certifications: Any specific certifications required (if mentioned)
        
        Be thorough and extract all relevant information. If something is not mentioned, 
        use null or empty lists as appropriate.
        """
        
        structured_jd, status = await handler.invoke_structured(
            prompt="Analyze this job description:",
            system_prompt=system_prompt,
            response_schema=StructuredJD,
            user_content=jd_text
        )
        
        return structured_jd, status
        
    except Exception as e:
        # Return error with partial structure
        error_jd = StructuredJD(
            role_title="Unknown",
            role_summary=str(e),
            mandatory_skills=[],
            preferred_skills=[],
            experience_requirements={},
            role_seniority="Unknown"
        )
        return error_jd, 400
