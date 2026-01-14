"""Experience Evaluation Agent - Assesses experience relevance"""
from schema.resume_screening import StructuredJD, StructuredResume, ExperienceEvaluationResult
from typing import Tuple
from logic.llm_handler import LLMHandler


async def evaluate_experience(
    structured_jd: StructuredJD,
    structured_resume: StructuredResume,
    handler: LLMHandler
) -> Tuple[ExperienceEvaluationResult, int]:
    """
    Evaluate candidate's experience against JD requirements.
    
    Returns:
        Tuple of (ExperienceEvaluationResult, status_code)
    """
    try:
        
        experience_details_str = "\n".join([
            f"- {exp.get('role', 'Unknown')} at {exp.get('company', 'Unknown')} ({exp.get('years', 0)} years): {exp.get('description', 'No description')}"
            for exp in structured_resume.experience
        ]) if structured_resume.experience else "No experience listed"
        
        system_prompt = f"""
        Evaluate the candidate's work experience against the job description requirements.
        
        Job Description Requirements:
        - Role: {structured_jd.role_title}
        - Role Summary: {structured_jd.role_summary}
        - Experience Requirements: {str(structured_jd.experience_requirements)}
        - Role Seniority: {structured_jd.role_seniority}
        
        Candidate Experience:
        - Total Years: {structured_resume.total_years_experience}
        - Experience Details: {experience_details_str}
        
        MISSING DATA HANDLING:
        - If candidate has no experience listed: 
          * total_relevant_experience_years = 0
          * domain_relevance_score = 0
          * role_alignment_score = 0
          * overqualification_flag = false
          * irrelevant_experience_penalty = 0
        - If experience is listed but lacks details (no years, no descriptions):
          * Estimate conservatively (lower scores)
          * Note missing information in explanation
        
        Your task:
        1. Calculate total_relevant_experience_years (only count experience relevant to JD)
           - If no experience listed: return 0
        2. Assess domain_relevance_score (0-100): How relevant is the candidate's domain experience?
           - If no experience: score = 0
        3. Assess role_alignment_score (0-100): How well does the experience align with the role?
           - If no experience: score = 0
        4. Check overqualification_flag: Is the candidate significantly overqualified?
           - Only true if experience significantly exceeds requirements
        5. Calculate irrelevant_experience_penalty (0-1): Penalty for irrelevant experience
           - If no experience: penalty = 0 (not penalized for missing data, just scored as 0)
        6. Explain your evaluation and note any missing experience data
        
        Guidelines:
        - Penalize overqualification (e.g., Senior applying for Junior role)
        - Penalize irrelevant experience (e.g., Marketing experience for Software Engineer role)
        - Reward relevant domain experience
        - Consider role progression and career trajectory
        
        All scores must be between 0-100.
        """
        
        experience_result, status = await handler.invoke_structured(
            prompt="Please evaluate the candidate's experience.",
            system_prompt=system_prompt,
            response_schema=ExperienceEvaluationResult
        )
        
        return experience_result, status
        
    except Exception as e:
        # Return error result
        error_result = ExperienceEvaluationResult(
            total_relevant_experience_years=0.0,
            domain_relevance_score=0.0,
            role_alignment_score=0.0,
            overqualification_flag=False,
            irrelevant_experience_penalty=1.0,
            experience_explanation=f"Error in experience evaluation: {str(e)}"
        )
        return error_result, 400
