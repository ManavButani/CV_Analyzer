"""Resume Screening Orchestrator - Coordinates all sub-agents"""
from typing import List, Tuple, Dict, Any
from sqlalchemy.orm import Session
from schema.resume_screening import (
    ResumeScreeningRequest, ResumeScreeningResponse, ScreeningSummary
)
from logic.file_parser import extract_text_from_file
from logic.jd_analyzer import analyze_jd
from logic.combined_analyzer import analyze_resume_combined
from logic.scoring_ranker import rank_candidates
from logic.utils import get_traceback_string
from logic.llm_handler import LLMHandler
from schema.resume_screening import (
    StructuredResume, SkillMatchResult, ExperienceEvaluationResult,
    CandidateScore, CandidateExplanation
)


async def orchestrate_resume_screening(
    request: ResumeScreeningRequest,
    db: Session
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
        # Create single handler for entire request
        handler = LLMHandler(db)
        
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
        
        structured_jd, jd_status = await analyze_jd(
            jd_text=jd_text,
            handler=handler
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
        
        # Step 2 & 3: Analyze all resumes (single API call per resume)
        ranked_data = []
        
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
                    continue
            except Exception as e:
                intermediate_outputs["resume_parsing"][f"resume_{idx}"] = {
                    "status": "error",
                    "error": f"Failed to parse resume file: {str(e)}"
                }
                continue
            
            # Single API call for combined analysis
            combined_result, analysis_status = await analyze_resume_combined(
                resume_text=resume_text,
                structured_jd=structured_jd,
                scoring_weights=request.scoring_weights or {},
                handler=handler,
                candidate_name=resume_input.candidate_name
            )
            
            if analysis_status == 200:
                # Use nested schemas directly from combined result
                structured_resume = combined_result.structured_resume
                structured_resume.raw_text = resume_text  # Ensure raw_text is set
                
                skill_match = combined_result.skill_match
                experience_eval = combined_result.experience_eval
                candidate_score = combined_result.candidate_score
                candidate_explanation = combined_result.candidate_explanation
                
                intermediate_outputs["resume_parsing"][f"resume_{idx}"] = {
                    "status": "success",
                    "candidate_name": structured_resume.candidate_name
                }
                intermediate_outputs["skill_matching"][f"resume_{idx}"] = {
                    "status": "success",
                    "skill_match_score": skill_match.skill_match_score
                }
                intermediate_outputs["experience_evaluation"][f"resume_{idx}"] = {
                    "status": "success",
                    "domain_relevance": experience_eval.domain_relevance_score
                }
                intermediate_outputs["scoring"][f"resume_{idx}"] = {
                    "status": "success",
                    "overall_score": candidate_score.weighted_total_score
                }
                
                ranked_data.append((
                    structured_resume,
                    candidate_score,
                    candidate_explanation,
                    skill_match,
                    experience_eval
                ))
            else:
                intermediate_outputs["resume_parsing"][f"resume_{idx}"] = {
                    "status": "error",
                    "error": "Failed to analyze resume"
                }
        
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
        ranked_candidates, summary, rank_status = await rank_candidates(
            ranked_data=ranked_data,
            structured_jd=structured_jd,
            handler=handler
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
                "total_resumes_processed": len(request.resumes),
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
