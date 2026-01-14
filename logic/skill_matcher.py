"""Skill Matching Agent - Matches resume skills against JD skills"""
from schema.resume_screening import StructuredJD, StructuredResume, SkillMatchResult
from typing import Tuple
from logic.llm_handler import LLMHandler


async def match_skills(
    structured_jd: StructuredJD,
    structured_resume: StructuredResume,
    handler: LLMHandler
) -> Tuple[SkillMatchResult, int]:
    """
    Match resume skills against JD skills with synonym and partial match handling.
    
    Returns:
        Tuple of (SkillMatchResult, status_code)
    """
    try:
        
        mandatory_skills_str = ", ".join(structured_jd.mandatory_skills) if structured_jd.mandatory_skills else "None"
        preferred_skills_str = ", ".join(structured_jd.preferred_skills) if structured_jd.preferred_skills else "None"
        candidate_skills_str = ", ".join(structured_resume.skills) if structured_resume.skills else "None"
        
        system_prompt = f"""
        Match the candidate's skills from their resume against the job description requirements.
        
        Job Description Skills:
        - Mandatory Skills (Required): {mandatory_skills_str}
        - Preferred Skills (Nice-to-have): {preferred_skills_str}
        
        Candidate Skills: {candidate_skills_str}
        
        MISSING DATA HANDLING:
        - If candidate has no skills listed: skill_match_score = 0
        - If mandatory skills are missing: penalize heavily (each missing mandatory skill reduces score)
        - If preferred skills are missing: penalize moderately
        - If candidate has skills but none match JD: skill_match_score = 0
        
        Your task:
        1. Identify which mandatory skills are matched (handle synonyms, e.g., "PyTorch" vs "Deep Learning")
        2. Identify which preferred skills are matched
        3. List missing mandatory skills (critical - these must be present)
        4. List missing preferred skills (nice to have)
        5. Calculate a skill match score (0-100) based on:
           - 70% weight on mandatory skills match (if all mandatory skills matched = 70 points)
           - 30% weight on preferred skills match (if all preferred skills matched = 30 points)
           - If no candidate skills listed: score = 0
           - If mandatory skills exist but none matched: score = 0
        6. Provide a clear explanation of matches/mismatches, including synonym handling and note any missing data issues
        
        Be intelligent about matching:
        - Handle synonyms (e.g., "ML" = "Machine Learning", "JS" = "JavaScript")
        - Handle partial matches (e.g., "Python" matches "Python Programming")
        - Consider related technologies (e.g., "React" is related to "Frontend Development")
        """
        
        skill_match_result, status = await handler.invoke_structured(
            prompt="Please analyze and match the skills.",
            system_prompt=system_prompt,
            response_schema=SkillMatchResult
        )
        
        return skill_match_result, status
        
    except Exception as e:
        # Return error result
        error_result = SkillMatchResult(
            matched_mandatory_skills=[],
            matched_preferred_skills=[],
            missing_mandatory_skills=structured_jd.mandatory_skills.copy() if structured_jd.mandatory_skills else [],
            missing_preferred_skills=structured_jd.preferred_skills.copy() if structured_jd.preferred_skills else [],
            skill_match_score=0.0,
            skill_explanation=f"Error in skill matching: {str(e)}"
        )
        return error_result, 400
