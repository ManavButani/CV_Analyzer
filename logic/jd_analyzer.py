"""JD Analyzer Agent - Extracts structured information from Job Description"""
from openai import OpenAI
from schema.resume_screening import StructuredJD
from typing import Tuple


def analyze_jd(
    jd_text: str,
    api_key: str,
    model: str = "gpt-4o"
) -> Tuple[StructuredJD, int]:
    """
    Analyze Job Description and extract structured information.
    
    Returns:
        Tuple of (StructuredJD, status_code)
    """
    try:
        client = OpenAI(api_key=api_key)
        
        prompt = """
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
        
        completion = client.beta.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": jd_text}
            ],
            response_format=StructuredJD,
        )
        
        structured_jd = completion.choices[0].message.parsed
        return structured_jd, 200
        
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
