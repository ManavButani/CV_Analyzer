"""Combined Analyzer - Single API call for resume analysis"""
from schema.resume_screening import StructuredJD, CombinedAnalysisResult
from typing import Tuple
from logic.llm_handler import LLMHandler


async def analyze_resume_combined(
    resume_text: str,
    structured_jd: StructuredJD,
    scoring_weights: dict,
    handler: LLMHandler,
    candidate_name: str = None
) -> Tuple[CombinedAnalysisResult, int]:
    """
    Single LLM call that performs:
    1. Resume parsing
    2. Skill matching
    3. Experience evaluation
    4. Score calculation
    5. Explanation generation
    
    Returns:
        Tuple of (CombinedAnalysisResult, status_code)
    """
    try:
        # Normalize weights
        total_weight = sum(scoring_weights.values())
        if total_weight > 0:
            normalized_weights = {k: v / total_weight for k, v in scoring_weights.items()}
        else:
            normalized_weights = {
                "skills_match": 0.40,
                "relevant_experience": 0.35,
                "role_alignment": 0.15,
                "education_certifications": 0.10
            }
        
        mandatory_skills_str = ", ".join(structured_jd.mandatory_skills) if structured_jd.mandatory_skills else "None"
        preferred_skills_str = ", ".join(structured_jd.preferred_skills) if structured_jd.preferred_skills else "None"
        
        system_prompt = f"""
        You are an expert HR analyst. Perform comprehensive analysis of the candidate's resume against the job description.
        
        JOB DESCRIPTION:
        Role: {structured_jd.role_title}
        Summary: {structured_jd.role_summary}
        Mandatory Skills: {mandatory_skills_str}
        Preferred Skills: {preferred_skills_str}
        Experience Requirements: {str(structured_jd.experience_requirements)}
        Role Seniority: {structured_jd.role_seniority}
        Education Requirements: {', '.join(structured_jd.education_requirements) if structured_jd.education_requirements else 'None'}
        
        SCORING WEIGHTS:
        - Skills Match: {normalized_weights.get('skills_match', 0.40):.0%}
        - Relevant Experience: {normalized_weights.get('relevant_experience', 0.35):.0%}
        - Role Alignment: {normalized_weights.get('role_alignment', 0.15):.0%}
        - Education: {normalized_weights.get('education_certifications', 0.10):.0%}
        
        PERFORM ALL TASKS IN ONE ANALYSIS:
        
        1. RESUME PARSING (structured_resume):
           - Extract candidate_name, skills, experience (role, company, years, description)
           - Calculate total_years_experience
           - Extract projects, education, certifications
           - Set raw_text to the resume text provided
        
        2. SKILL MATCHING (skill_match):
           - Match mandatory skills (handle synonyms: "PyTorch"="Deep Learning", "ML"="Machine Learning")
           - Match preferred skills
           - List missing mandatory/preferred skills
           - Calculate skill_match_score (0-100): 70% mandatory, 30% preferred
           - Explain matches/mismatches in skill_explanation
        
        3. EXPERIENCE EVALUATION (experience_eval):
           - Calculate total_relevant_experience_years (only JD-relevant)
           - Assess domain_relevance_score (0-100)
           - Assess role_alignment_score (0-100)
           - Check overqualification_flag (boolean)
           - Calculate irrelevant_experience_penalty (0-1)
           - Explain evaluation in experience_explanation
        
        4. SCORING (candidate_score):
           - skills_score = skill_match_score
           - experience_score = (domain_relevance_score * 0.6 + role_alignment_score * 0.4)
             * Apply 0.8 multiplier if overqualification_flag is true
             * Apply (1 - irrelevant_experience_penalty * 0.3) multiplier
           - role_alignment_score = role_alignment_score from experience_eval
           - education_score = 100 if no requirement, else based on education match
           - weighted_total_score = (skills_score * {normalized_weights.get('skills_match', 0.40):.2f}) + 
             (experience_score * {normalized_weights.get('relevant_experience', 0.35):.2f}) + 
             (role_alignment_score * {normalized_weights.get('role_alignment', 0.15):.2f}) + 
             (education_score * {normalized_weights.get('education_certifications', 0.10):.2f})
           - Provide scoring_explanation
        
        5. EXPLANATION (candidate_explanation):
           - Generate strengths, gaps, missing_requirements, risk_flags
           - Provide comprehensive reasoning
           - Set overall_match_score = weighted_total_score
           - Set rank_position = 0 (will be set later)
        
        All scores must be between 0-100. Return structured data matching the CombinedAnalysisResult schema.
        """
        
        user_content = resume_text
        if candidate_name:
            user_content = f"Candidate Name (if not in resume): {candidate_name}\n\n{resume_text}"
        
        result, status = await handler.invoke_structured(
            prompt="Analyze this resume comprehensively:",
            system_prompt=system_prompt,
            response_schema=CombinedAnalysisResult,
            user_content=user_content
        )
        
        return result, status
        
    except Exception as e:
        from schema.resume_screening import StructuredResume, SkillMatchResult, ExperienceEvaluationResult, CandidateScore, CandidateExplanation
        
        error_result = CombinedAnalysisResult(
            structured_resume=StructuredResume(
                candidate_name=candidate_name or "Unknown",
                skills=[],
                experience=[],
                total_years_experience=0.0,
                raw_text=resume_text
            ),
            skill_match=SkillMatchResult(
                matched_mandatory_skills=[],
                matched_preferred_skills=[],
                missing_mandatory_skills=structured_jd.mandatory_skills.copy() if structured_jd.mandatory_skills else [],
                missing_preferred_skills=structured_jd.preferred_skills.copy() if structured_jd.preferred_skills else [],
                skill_match_score=0.0,
                skill_explanation=f"Error: {str(e)}"
            ),
            experience_eval=ExperienceEvaluationResult(
                total_relevant_experience_years=0.0,
                domain_relevance_score=0.0,
                role_alignment_score=0.0,
                overqualification_flag=False,
                irrelevant_experience_penalty=1.0,
                experience_explanation=f"Error: {str(e)}"
            ),
            candidate_score=CandidateScore(
                skills_score=0.0,
                experience_score=0.0,
                role_alignment_score=0.0,
                education_score=0.0,
                weighted_total_score=0.0,
                scoring_explanation=f"Error: {str(e)}"
            ),
            candidate_explanation=CandidateExplanation(
                rank_position=0,
                overall_match_score=0.0,
                strengths=[],
                gaps=[],
                missing_requirements=[],
                risk_flags=["Error in analysis"],
                reasoning=f"Error: {str(e)}"
            )
        )
        return error_result, 400
