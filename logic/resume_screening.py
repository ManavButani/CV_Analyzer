"""Resume Screening Orchestrator - Coordinates all sub-agents"""
from typing import List, Tuple, Dict, Any
import os
from dotenv import load_dotenv
from schema.resume_screening import (
    ResumeScreeningRequest, ResumeScreeningResponse,
    StructuredJD, StructuredResume, SkillMatchResult,
    ExperienceEvaluationResult, CandidateScore, CandidateExplanation,
    RankedCandidate, ScreeningSummary
)
from logic.file_parser import extract_text_from_file
from logic.jd_analyzer import analyze_jd
from logic.resume_parser import parse_resume
from logic.skill_matcher import match_skills
from logic.experience_evaluator import evaluate_experience
from logic.scoring_ranker import calculate_candidate_score, rank_candidates
from logic.utils import get_traceback_string

load_dotenv()


def orchestrate_resume_screening(
    request: ResumeScreeningRequest
) -> Tuple[ResumeScreeningResponse, int]:
    """
    Main orchestrator function that coordinates all sub-agents.
    
    Pipeline:
    1. Parse JD and extract structured information
    2. Parse all resumes and extract structured information
    3. For each resume:
       a. Match skills against JD
       b. Evaluate experience
       c. Calculate scores
    4. Rank all candidates
    5. Generate final summary
    
    Returns:
        Tuple of (ResumeScreeningResponse, status_code)
    """
    try:
        # Get OpenAI API key (from request or .env)
        api_key = request.openai_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            error_response = ResumeScreeningResponse(
                ranked_candidates=[],
                summary=ScreeningSummary(
                    top_3_candidates=[],
                    common_gaps_observed=["OpenAI API key is required"],
                    hiring_risks=["Configuration error"],
                    overall_statistics={}
                ),
                scoring_weights_used=request.scoring_weights or {},
                processing_metadata={"error": "OpenAI API key not provided"}
            )
            return error_response, 400
        
        # Track intermediate outputs for debugging/explainability
        intermediate_outputs = {
            "jd_parsing": {},
            "resume_parsing": {},
            "skill_matching": {},
            "experience_evaluation": {},
            "scoring": {}
        }
        
        # Step 1: Parse JD
        jd_text = None
        if request.jd.jd_text:
            jd_text = request.jd.jd_text
        elif request.jd.jd_file:
            try:
                jd_text = extract_text_from_file(
                    base64_content=request.jd.jd_file,
                    file_format=request.jd.file_format.value if request.jd.file_format else "txt"
                )
            except Exception as e:
                error_response = ResumeScreeningResponse(
                    ranked_candidates=[],
                    summary=ScreeningSummary(
                        top_3_candidates=[],
                        common_gaps_observed=[f"Failed to parse JD file: {str(e)}"],
                        hiring_risks=["JD parsing error"],
                        overall_statistics={"error": str(e)}
                    ),
                    scoring_weights_used=request.scoring_weights,
                    processing_metadata={"error": f"JD parsing failed: {str(e)}"}
                )
                return error_response, 400
        else:
            error_response = ResumeScreeningResponse(
                ranked_candidates=[],
                summary=ScreeningSummary(
                    top_3_candidates=[],
                    common_gaps_observed=["No JD provided (neither text nor file)"],
                    hiring_risks=["Invalid input"],
                    overall_statistics={}
                ),
                scoring_weights_used=request.scoring_weights,
                processing_metadata={"error": "No JD provided"}
            )
            return error_response, 400
        
        structured_jd, jd_status = analyze_jd(
            jd_text=jd_text,
            api_key=api_key,
            model=request.model
        )
        
        if jd_status != 200:
            error_response = ResumeScreeningResponse(
                ranked_candidates=[],
                summary=ScreeningSummary(
                    top_3_candidates=[],
                    common_gaps_observed=[f"Failed to analyze JD: {structured_jd.role_summary}"],
                    hiring_risks=["JD analysis failed"],
                    overall_statistics={"error": "JD analysis failed"}
                ),
                scoring_weights_used=request.scoring_weights,
                processing_metadata={"error": "JD analysis failed", "jd_status": jd_status}
            )
            return error_response, jd_status
        
        intermediate_outputs["jd_parsing"] = {
            "status": "success",
            "role_title": structured_jd.role_title,
            "mandatory_skills_count": len(structured_jd.mandatory_skills),
            "preferred_skills_count": len(structured_jd.preferred_skills)
        }
        
        # Step 2: Parse all resumes
        structured_resumes = []
        for idx, resume_input in enumerate(request.resumes):
            resume_text = None
            try:
                if resume_input.resume_text:
                    resume_text = resume_input.resume_text
                elif resume_input.resume_file:
                    resume_text = extract_text_from_file(
                        base64_content=resume_input.resume_file,
                        file_format=resume_input.file_format.value if resume_input.file_format else "txt"
                    )
                else:
                    intermediate_outputs["resume_parsing"][f"resume_{idx}"] = {
                        "status": "skipped",
                        "error": "No resume text or file provided"
                    }
                    continue  # Skip invalid resume
            except Exception as e:
                intermediate_outputs["resume_parsing"][f"resume_{idx}"] = {
                    "status": "error",
                    "error": f"Failed to parse resume file: {str(e)}"
                }
                continue  # Skip resume with parsing error
            
            structured_resume, resume_status = parse_resume(
                resume_text=resume_text,
                candidate_name=resume_input.candidate_name,
                api_key=api_key,
                model=request.model
            )
            
            if resume_status == 200:
                structured_resumes.append(structured_resume)
                intermediate_outputs["resume_parsing"][f"resume_{idx}"] = {
                    "status": "success",
                    "candidate_name": structured_resume.candidate_name,
                    "skills_count": len(structured_resume.skills),
                    "experience_count": len(structured_resume.experience)
                }
            else:
                intermediate_outputs["resume_parsing"][f"resume_{idx}"] = {
                    "status": "error",
                    "error": "Failed to parse resume"
                }
        
        if not structured_resumes:
            error_response = ResumeScreeningResponse(
                ranked_candidates=[],
                summary=ScreeningSummary(
                    top_3_candidates=[],
                    common_gaps_observed=["No valid resumes could be parsed"],
                    hiring_risks=["Resume parsing failed"],
                    overall_statistics={}
                ),
                scoring_weights_used=request.scoring_weights,
                processing_metadata=intermediate_outputs
            )
            return error_response, 400
        
        # Step 3: Evaluate each resume
        ranked_data = []
        
        for idx, structured_resume in enumerate(structured_resumes):
            try:
                # 3a. Match skills
                skill_match, skill_status = match_skills(
                    structured_jd=structured_jd,
                    structured_resume=structured_resume,
                    api_key=api_key,
                    model=request.model
                )
                
                intermediate_outputs["skill_matching"][f"resume_{idx}"] = {
                    "status": "success" if skill_status == 200 else "error",
                    "skill_match_score": skill_match.skill_match_score if skill_status == 200 else 0.0
                }
                
                # 3b. Evaluate experience
                experience_eval, exp_status = evaluate_experience(
                    structured_jd=structured_jd,
                    structured_resume=structured_resume,
                    api_key=api_key,
                    model=request.model
                )
                
                intermediate_outputs["experience_evaluation"][f"resume_{idx}"] = {
                    "status": "success" if exp_status == 200 else "error",
                    "domain_relevance": experience_eval.domain_relevance_score if exp_status == 200 else 0.0
                }
                
                # 3c. Calculate scores
                candidate_score, candidate_explanation, score_status = calculate_candidate_score(
                    skill_match=skill_match,
                    experience_eval=experience_eval,
                    structured_resume=structured_resume,
                    structured_jd=structured_jd,
                    scoring_weights=request.scoring_weights,
                    api_key=api_key,
                    model=request.model
                )
                
                intermediate_outputs["scoring"][f"resume_{idx}"] = {
                    "status": "success" if score_status == 200 else "error",
                    "overall_score": candidate_score.weighted_total_score if score_status == 200 else 0.0
                }
                
                # Store for ranking
                ranked_data.append((
                    structured_resume,
                    candidate_score,
                    candidate_explanation,
                    skill_match,
                    experience_eval
                ))
                
            except Exception as e:
                # Handle failures gracefully - continue with other resumes
                intermediate_outputs["scoring"][f"resume_{idx}"] = {
                    "status": "error",
                    "error": str(e)
                }
                continue
        
        if not ranked_data:
            error_response = ResumeScreeningResponse(
                ranked_candidates=[],
                summary=ScreeningSummary(
                    top_3_candidates=[],
                    common_gaps_observed=["No candidates could be evaluated"],
                    hiring_risks=["Evaluation failed"],
                    overall_statistics={}
                ),
                scoring_weights_used=request.scoring_weights,
                processing_metadata=intermediate_outputs
            )
            return error_response, 400
        
        # Step 4: Rank candidates
        ranked_candidates, summary, rank_status = rank_candidates(
            ranked_data=ranked_data,
            structured_jd=structured_jd,
            api_key=api_key,
            model=request.model
        )
        
        if rank_status != 200:
            error_response = ResumeScreeningResponse(
                ranked_candidates=[],
                summary=summary,
                scoring_weights_used=request.scoring_weights,
                processing_metadata=intermediate_outputs
            )
            return error_response, rank_status
        
        # Step 5: Build final response
        response = ResumeScreeningResponse(
            ranked_candidates=ranked_candidates,
            summary=summary,
            scoring_weights_used=request.scoring_weights,
            processing_metadata={
                "total_resumes_processed": len(structured_resumes),
                "total_candidates_ranked": len(ranked_candidates),
                "intermediate_outputs": intermediate_outputs
            }
        )
        
        return response, 200
        
    except Exception as e:
        # Return error response with traceback
        traceback_str = get_traceback_string()
        error_response = ResumeScreeningResponse(
            ranked_candidates=[],
            summary=ScreeningSummary(
                top_3_candidates=[],
                common_gaps_observed=[f"Orchestration error: {str(e)}"],
                hiring_risks=["System error occurred"],
                overall_statistics={"error": str(e)}
            ),
            scoring_weights_used=request.scoring_weights if request else {},
            processing_metadata={
                "error": str(e),
                "traceback": traceback_str
            }
        )
        return error_response, 500
