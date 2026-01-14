"""Skill Matching Agent - Matches resume skills against JD skills"""
from openai import OpenAI
from schema.resume_screening import StructuredJD, StructuredResume, SkillMatchResult
from typing import Tuple


def match_skills(
    structured_jd: StructuredJD,
    structured_resume: StructuredResume,
    api_key: str,
    model: str = "gpt-4o"
) -> Tuple[SkillMatchResult, int]:
    """
    Match resume skills against JD skills with synonym and partial match handling.
    
    Returns:
        Tuple of (SkillMatchResult, status_code)
    """
    try:
        client = OpenAI(api_key=api_key)
        
        prompt = """
        Match the candidate's skills from their resume against the job description requirements.
        
        Job Description Skills:
        - Mandatory Skills (Required): {mandatory_skills}
        - Preferred Skills (Nice-to-have): {preferred_skills}
        
        Candidate Skills: {candidate_skills}
        
        Your task:
        1. Identify which mandatory skills are matched (handle synonyms, e.g., "PyTorch" vs "Deep Learning")
        2. Identify which preferred skills are matched
        3. List missing mandatory skills
        4. List missing preferred skills
        5. Calculate a skill match score (0-100) based on:
           - Mandatory skills match: 70% weight
           - Preferred skills match: 30% weight
        6. Provide a clear explanation of matches/mismatches, including synonym handling
        
        Be intelligent about matching:
        - Handle synonyms (e.g., "ML" = "Machine Learning", "JS" = "JavaScript")
        - Handle partial matches (e.g., "Python" matches "Python Programming")
        - Consider related technologies (e.g., "React" is related to "Frontend Development")
        """
        
        mandatory_skills_str = ", ".join(structured_jd.mandatory_skills) if structured_jd.mandatory_skills else "None"
        preferred_skills_str = ", ".join(structured_jd.preferred_skills) if structured_jd.preferred_skills else "None"
        candidate_skills_str = ", ".join(structured_resume.skills) if structured_resume.skills else "None"
        
        formatted_prompt = prompt.format(
            mandatory_skills=mandatory_skills_str,
            preferred_skills=preferred_skills_str,
            candidate_skills=candidate_skills_str
        )
        
        completion = client.beta.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": formatted_prompt},
                {"role": "user", "content": "Please analyze and match the skills."}
            ],
            response_format=SkillMatchResult,
        )
        
        skill_match_result = completion.choices[0].message.parsed
        return skill_match_result, 200
        
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
