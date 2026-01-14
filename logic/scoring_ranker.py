"""Scoring & Ranking Agent - Combines all signals into final scores and ranks candidates"""
from schema.resume_screening import (
    StructuredJD, StructuredResume, SkillMatchResult, 
    ExperienceEvaluationResult, CandidateScore, CandidateExplanation,
    RankedCandidate, ScreeningSummary
)
from typing import List, Dict, Tuple
from logic.llm_handler import LLMHandler


async def calculate_candidate_score(
    skill_match: SkillMatchResult,
    experience_eval: ExperienceEvaluationResult,
    structured_resume: StructuredResume,
    structured_jd: StructuredJD,
    scoring_weights: Dict[str, float],
    handler: LLMHandler
) -> Tuple[CandidateScore, CandidateExplanation, int]:
    """
    Calculate final score and generate explanation for a candidate.
    
    MISSING DATA HANDLING:
    - Missing skills: Penalized in skill_match_score (0% for missing mandatory skills)
    - Missing experience: If no experience listed, experience_score = 0
    - Missing education: If JD requires education but resume has none, education_score = 0
    - Missing certifications: If JD requires but resume has none, small penalty applied
    - Missing projects: No penalty (optional field)
    
    Returns:
        Tuple of (CandidateScore, CandidateExplanation, status_code)
    """
    try:
        # Normalize weights to ensure they sum to 1.0
        total_weight = sum(scoring_weights.values())
        if total_weight > 0:
            normalized_weights = {k: v / total_weight for k, v in scoring_weights.items()}
        else:
            # Default weights if none provided
            normalized_weights = {
                "skills_match": 0.40,
                "relevant_experience": 0.35,
                "role_alignment": 0.15,
                "education_certifications": 0.10
            }
        
        # Calculate education score with explicit missing data handling
        education_score = 0.0
        if structured_jd.education_requirements and len(structured_jd.education_requirements) > 0:
            # JD requires education
            if not structured_resume.education or len(structured_resume.education) == 0:
                # MISSING DATA: No education listed when required = 0 score
                education_score = 0.0
            else:
                # Check if any education matches requirements (simple matching)
                # Award partial score based on number of education entries
                education_score = min(100.0, len(structured_resume.education) * 50.0)
        else:
            # No education requirement = full score (no penalty for missing data)
            education_score = 100.0
        
        # Handle missing experience data
        if not structured_resume.experience or len(structured_resume.experience) == 0:
            # MISSING DATA: No experience listed
            # This will be reflected in experience_eval, but we ensure it's penalized
            if experience_eval.total_relevant_experience_years == 0:
                experience_eval.domain_relevance_score = 0.0
                experience_eval.role_alignment_score = 0.0
        
        # Calculate component scores with missing data handling
        skills_score = skill_match.skill_match_score
        # MISSING DATA: If no skills listed, skill_match_score should already be 0 from skill_matcher
        
        # Calculate experience score
        if not structured_resume.experience or len(structured_resume.experience) == 0:
            # MISSING DATA: No experience listed = 0 experience score
            experience_score = 0.0
            role_alignment_score = 0.0
        else:
            experience_score = (
                experience_eval.domain_relevance_score * 0.6 + 
                experience_eval.role_alignment_score * 0.4
            )
            role_alignment_score = experience_eval.role_alignment_score
            
            # Apply penalties for overqualification and irrelevant experience
            if experience_eval.overqualification_flag:
                experience_score *= 0.8  # 20% penalty for overqualification
            
            experience_score *= (1.0 - experience_eval.irrelevant_experience_penalty * 0.3)
        
        # Ensure scores are within valid range [0, 100]
        skills_score = max(0.0, min(100.0, skills_score))
        experience_score = max(0.0, min(100.0, experience_score))
        role_alignment_score = max(0.0, min(100.0, role_alignment_score))
        education_score = max(0.0, min(100.0, education_score))
        
        # Calculate weighted total
        weighted_total = (
            skills_score * normalized_weights.get("skills_match", 0.40) +
            experience_score * normalized_weights.get("relevant_experience", 0.35) +
            role_alignment_score * normalized_weights.get("role_alignment", 0.15) +
            education_score * normalized_weights.get("education_certifications", 0.10)
        )
        
        # Track missing data flags for explanation
        missing_data_flags = []
        if not structured_resume.skills or len(structured_resume.skills) == 0:
            missing_data_flags.append("No skills listed in resume")
        if not structured_resume.experience or len(structured_resume.experience) == 0:
            missing_data_flags.append("No work experience listed")
        if structured_jd.education_requirements and (not structured_resume.education or len(structured_resume.education) == 0):
            missing_data_flags.append("No education listed (required by JD)")
        if skill_match.missing_mandatory_skills:
            missing_data_flags.append(f"Missing mandatory skills: {', '.join(skill_match.missing_mandatory_skills[:3])}")
        
        # Generate explanation using AI
        try:
            missing_data_note = ""
            if missing_data_flags:
                missing_data_note = f"\n\nMISSING DATA DETECTED:\n" + "\n".join([f"- {flag}" for flag in missing_data_flags])
            
            explanation_prompt = f"""
            Generate a comprehensive explanation for this candidate's ranking.
            
            Candidate: {structured_resume.candidate_name or 'Unknown'}
            Role: {structured_jd.role_title}
            
            Scores:
            - Skills Match: {skills_score:.1f}/100
            - Experience: {experience_score:.1f}/100
            - Role Alignment: {role_alignment_score:.1f}/100
            - Education: {education_score:.1f}/100
            - Overall Score: {weighted_total:.1f}/100
            {missing_data_note}
            
            Skill Analysis:
            {skill_match.skill_explanation}
            
            Experience Analysis:
            {experience_eval.experience_explanation}
            
            Provide:
            1. List of strengths (bullet points)
            2. List of gaps/missing requirements (bullet points) - include any missing data issues
            3. List of risk flags (if any) - include missing mandatory requirements
            4. Overall reasoning for the score - explain how missing data affected the score
            
            Format as clear bullet points.
            """
            
            explanation_text, _ = await handler.invoke_text(
                prompt=explanation_prompt,
                system_prompt="You are an expert HR analyst providing candidate evaluation explanations.",
                temperature=0.3
            )
            
            # Parse explanation into structured format (simplified)
            strengths = []
            gaps = []
            risk_flags = []
            
            # Simple parsing - can be enhanced with structured output
            lines = explanation_text.split('\n')
            current_section = None
            for line in lines:
                line = line.strip()
                if 'strength' in line.lower() or 'strong' in line.lower():
                    current_section = 'strengths'
                elif 'gap' in line.lower() or 'missing' in line.lower():
                    current_section = 'gaps'
                elif 'risk' in line.lower() or 'flag' in line.lower():
                    current_section = 'risks'
                elif line.startswith('-') or line.startswith('•') or line.startswith('*'):
                    content = line.lstrip('-•*').strip()
                    if current_section == 'strengths' and content:
                        strengths.append(content)
                    elif current_section == 'gaps' and content:
                        gaps.append(content)
                    elif current_section == 'risks' and content:
                        risk_flags.append(content)
            
            # If parsing failed, use full explanation
            if not strengths and not gaps:
                strengths = [explanation_text[:200] + "..."] if explanation_text else []
            
        except Exception as e:
            # Fallback explanation
            explanation_text = f"Score calculated based on skills ({skills_score:.1f}%), experience ({experience_score:.1f}%), role alignment ({role_alignment_score:.1f}%), and education ({education_score:.1f}%)."
            strengths = [f"Skills match: {skill_match.skill_match_score:.1f}%"]
            gaps = skill_match.missing_mandatory_skills
            risk_flags = []
            if experience_eval.overqualification_flag:
                risk_flags.append("Candidate may be overqualified")
        
        candidate_score = CandidateScore(
            skills_score=skills_score,
            experience_score=experience_score,
            role_alignment_score=role_alignment_score,
            education_score=education_score,
            weighted_total_score=weighted_total,
            scoring_explanation=f"Skills: {skills_score:.1f}% (weight: {normalized_weights.get('skills_match', 0.40):.0%}), "
                              f"Experience: {experience_score:.1f}% (weight: {normalized_weights.get('relevant_experience', 0.35):.0%}), "
                              f"Role Alignment: {role_alignment_score:.1f}% (weight: {normalized_weights.get('role_alignment', 0.15):.0%}), "
                              f"Education: {education_score:.1f}% (weight: {normalized_weights.get('education_certifications', 0.10):.0%})"
        )
        
        candidate_explanation = CandidateExplanation(
            rank_position=0,  # Will be set during ranking
            overall_match_score=weighted_total,
            strengths=strengths,
            gaps=gaps,
            missing_requirements=skill_match.missing_mandatory_skills,
            risk_flags=risk_flags,
            reasoning=explanation_text
        )
        
        return candidate_score, candidate_explanation, 200
        
    except Exception as e:
        # Return error result
        error_score = CandidateScore(
            skills_score=0.0,
            experience_score=0.0,
            role_alignment_score=0.0,
            education_score=0.0,
            weighted_total_score=0.0,
            scoring_explanation=f"Error in scoring: {str(e)}"
        )
        error_explanation = CandidateExplanation(
            rank_position=0,
            overall_match_score=0.0,
            strengths=[],
            gaps=[],
            missing_requirements=[],
            risk_flags=["Error in evaluation"],
            reasoning=f"Error occurred during scoring: {str(e)}"
        )
        return error_score, error_explanation, 400


async def rank_candidates(
    ranked_data: List[Tuple[StructuredResume, CandidateScore, CandidateExplanation, SkillMatchResult, ExperienceEvaluationResult]],
    structured_jd: StructuredJD,
    handler: LLMHandler
) -> Tuple[List[RankedCandidate], ScreeningSummary, int]:
    """
    Rank candidates and generate final summary.
    
    TIE RESOLUTION LOGIC (applied in order):
    1. Primary: Weighted total score (descending)
    2. Secondary: Skills match score (descending) - candidates with better skill matches rank higher
    3. Tertiary: Experience score (descending) - candidates with more relevant experience rank higher
    4. Quaternary: Role alignment score (descending) - better role fit ranks higher
    5. Final: Education score (descending) - if all else equal, better education ranks higher
    
    If all scores are identical, candidates maintain their original order (stable sort).
    
    Returns:
        Tuple of (List[RankedCandidate], ScreeningSummary, status_code)
    """
    try:
        # TIE RESOLUTION: Multi-key sort with explicit tie-breaking criteria
        sorted_data = sorted(
            ranked_data,
            key=lambda x: (
                -x[1].weighted_total_score,  # Primary: total score (negative for descending)
                -x[1].skills_score,          # Secondary: skills match
                -x[1].experience_score,      # Tertiary: experience
                -x[4].role_alignment_score,  # Quaternary: role alignment (from experience_eval)
                -x[1].education_score        # Final: education
            )
        )
        
        # Create ranked candidates
        ranked_candidates = []
        for rank, (resume, score, explanation, skill_match, exp_eval) in enumerate(sorted_data, 1):
            explanation.rank_position = rank
            ranked_candidate = RankedCandidate(
                candidate_name=resume.candidate_name,
                rank=rank,
                overall_score=score.weighted_total_score,
                score_breakdown=score,
                explanation=explanation,
                structured_resume=resume
            )
            ranked_candidates.append(ranked_candidate)
        
        # Generate summary
        summary = await generate_summary(ranked_candidates, structured_jd, handler)
        
        return ranked_candidates, summary, 200
        
    except Exception as e:
        # Return error result
        error_summary = ScreeningSummary(
            top_3_candidates=[],
            common_gaps_observed=[f"Error in ranking: {str(e)}"],
            hiring_risks=["System error occurred"],
            overall_statistics={}
        )
        return [], error_summary, 400


async def generate_summary(
    ranked_candidates: List[RankedCandidate],
    structured_jd: StructuredJD,
    handler: LLMHandler
) -> ScreeningSummary:
    """Generate final summary of the screening process"""
    try:
        # Extract top 3
        top_3 = [
            {
                "name": c.candidate_name or f"Candidate {c.rank}",
                "score": c.overall_score,
                "rank": c.rank
            }
            for c in ranked_candidates[:3]
        ]
        
        # Calculate statistics
        if ranked_candidates:
            avg_score = sum(c.overall_score for c in ranked_candidates) / len(ranked_candidates)
            max_score = max(c.overall_score for c in ranked_candidates)
            min_score = min(c.overall_score for c in ranked_candidates)
        else:
            avg_score = max_score = min_score = 0.0
        
        # Collect common gaps and risks using AI
        try:
            gaps_text = "\n".join([
                f"- {gap}" for candidate in ranked_candidates[:5]
                for gap in candidate.explanation.gaps
            ])
            
            risks_text = "\n".join([
                f"- {risk}" for candidate in ranked_candidates[:5]
                for risk in candidate.explanation.risk_flags
            ])
            
            summary_prompt = f"""
            Analyze the screening results for this job: {structured_jd.role_title}
            
            Common Gaps Observed:
            {gaps_text[:1000]}
            
            Risk Flags:
            {risks_text[:1000]}
            
            Provide:
            1. List of most common gaps across candidates (3-5 items)
            2. List of hiring risks (e.g., talent scarcity, skill mismatch patterns)
            
            Format as clear bullet points.
            """
            
            summary_text, _ = await handler.invoke_text(
                prompt=summary_prompt,
                system_prompt="You are an expert HR analyst providing hiring insights.",
                temperature=0.3
            )
            
            # Parse summary (simplified)
            common_gaps = []
            hiring_risks = []
            lines = summary_text.split('\n')
            current_section = None
            for line in lines:
                line = line.strip()
                if 'gap' in line.lower():
                    current_section = 'gaps'
                elif 'risk' in line.lower():
                    current_section = 'risks'
                elif line.startswith('-') or line.startswith('•') or line.startswith('*'):
                    content = line.lstrip('-•*').strip()
                    if current_section == 'gaps' and content:
                        common_gaps.append(content)
                    elif current_section == 'risks' and content:
                        hiring_risks.append(content)
            
            if not common_gaps:
                common_gaps = ["No significant common gaps identified"]
            if not hiring_risks:
                hiring_risks = ["No major hiring risks identified"]
                
        except Exception as e:
            # Fallback
            common_gaps = ["Unable to analyze common gaps"]
            hiring_risks = ["Unable to analyze hiring risks"]
        
        summary = ScreeningSummary(
            top_3_candidates=top_3,
            common_gaps_observed=common_gaps[:5],
            hiring_risks=hiring_risks[:5],
            overall_statistics={
                "total_candidates": len(ranked_candidates),
                "average_score": round(avg_score, 2),
                "max_score": round(max_score, 2),
                "min_score": round(min_score, 2),
                "top_score": round(ranked_candidates[0].overall_score, 2) if ranked_candidates else 0.0
            }
        )
        
        return summary
        
    except Exception as e:
        # Return minimal summary
        return ScreeningSummary(
            top_3_candidates=[],
            common_gaps_observed=[f"Error generating summary: {str(e)}"],
            hiring_risks=["System error"],
            overall_statistics={"error": str(e)}
        )
