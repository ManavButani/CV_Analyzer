"""Experience Evaluation Agent - Assesses experience relevance"""
from openai import OpenAI
from schema.resume_screening import StructuredJD, StructuredResume, ExperienceEvaluationResult
from typing import Tuple


def evaluate_experience(
    structured_jd: StructuredJD,
    structured_resume: StructuredResume,
    api_key: str,
    model: str = "gpt-4o"
) -> Tuple[ExperienceEvaluationResult, int]:
    """
    Evaluate candidate's experience against JD requirements.
    
    Returns:
        Tuple of (ExperienceEvaluationResult, status_code)
    """
    try:
        client = OpenAI(api_key=api_key)
        
        prompt = """
        Evaluate the candidate's work experience against the job description requirements.
        
        Job Description Requirements:
        - Role: {role_title}
        - Role Summary: {role_summary}
        - Experience Requirements: {experience_requirements}
        - Role Seniority: {role_seniority}
        
        Candidate Experience:
        - Total Years: {total_years}
        - Experience Details: {experience_details}
        
        Your task:
        1. Calculate total relevant experience years (only count experience relevant to the JD)
        2. Assess domain relevance score (0-100): How well does their experience align with the domain/industry?
        3. Assess role alignment score (0-100): How well do their past roles align with the target role?
        4. Check for overqualification: Is the candidate significantly overqualified? (boolean)
        5. Calculate irrelevant experience penalty (0-1): Penalty for experience in completely unrelated fields
        6. Provide detailed explanation of the evaluation
        
        Guidelines:
        - Penalize overqualification (e.g., Senior applying for Junior role)
        - Penalize irrelevant experience (e.g., Marketing experience for Software Engineer role)
        - Reward relevant domain experience
        - Consider role progression and career trajectory
        """
        
        experience_details_str = "\n".join([
            f"- {exp.get('role', 'Unknown')} at {exp.get('company', 'Unknown')} ({exp.get('years', 0)} years): {exp.get('description', 'No description')}"
            for exp in structured_resume.experience
        ]) if structured_resume.experience else "No experience listed"
        
        formatted_prompt = prompt.format(
            role_title=structured_jd.role_title,
            role_summary=structured_jd.role_summary,
            experience_requirements=str(structured_jd.experience_requirements),
            role_seniority=structured_jd.role_seniority,
            total_years=structured_resume.total_years_experience,
            experience_details=experience_details_str
        )
        
        completion = client.beta.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": formatted_prompt},
                {"role": "user", "content": "Please evaluate the candidate's experience."}
            ],
            response_format=ExperienceEvaluationResult,
        )
        
        experience_result = completion.choices[0].message.parsed
        return experience_result, 200
        
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
