from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


class FileFormat(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"


class JDInput(BaseModel):
    """Job Description input - can be text or file"""
    jd_text: Optional[str] = None
    jd_file: Optional[str] = None  # Base64 encoded or file path
    file_format: Optional[FileFormat] = None


class ResumeInput(BaseModel):
    """Single resume input"""
    resume_text: Optional[str] = None
    resume_file: Optional[str] = None  # Base64 encoded or file path
    file_format: Optional[FileFormat] = None
    candidate_name: Optional[str] = None  # Optional identifier


class ResumeScreeningRequest(BaseModel):
    """Main request for resume screening"""
    jd: JDInput
    resumes: List[ResumeInput]
    scoring_weights: Optional[Dict[str, float]] = Field(
        default={
            "skills_match": 0.40,
            "relevant_experience": 0.35,
            "role_alignment": 0.15,
            "education_certifications": 0.10
        },
        description="Weight distribution for scoring (must sum to 1.0)"
    )


# Structured JD Schema
class StructuredJD(BaseModel):
    """Structured Job Description extracted by JD Analyzer"""
    role_title: str
    role_summary: str
    mandatory_skills: List[str]
    preferred_skills: List[str]
    experience_requirements: Dict[str, Any]  # e.g., {"min_years": 3, "domain": "Software Development"}
    role_seniority: str  # e.g., "Junior", "Mid-level", "Senior", "Lead"
    education_requirements: Optional[List[str]] = None
    certifications: Optional[List[str]] = None


# Structured Resume Schema
class StructuredResume(BaseModel):
    """Structured Resume data extracted by Resume Parser"""
    candidate_name: Optional[str] = None
    skills: List[str]
    experience: List[Dict[str, Any]]  # [{"role": "Software Engineer", "years": 3, "company": "X", "description": "..."}]
    total_years_experience: float
    projects: Optional[List[Dict[str, Any]]] = None
    education: Optional[List[Dict[str, Any]]] = None
    certifications: Optional[List[str]] = None
    raw_text: str  # Keep original for reference


# Skill Matching Output
class SkillMatchResult(BaseModel):
    """Skill matching analysis"""
    matched_mandatory_skills: List[str]
    matched_preferred_skills: List[str]
    missing_mandatory_skills: List[str]
    missing_preferred_skills: List[str]
    skill_match_score: float  # 0-100
    skill_explanation: str  # Explanation of matches/mismatches


# Experience Evaluation Output
class ExperienceEvaluationResult(BaseModel):
    """Experience evaluation analysis"""
    total_relevant_experience_years: float
    domain_relevance_score: float  # 0-100
    role_alignment_score: float  # 0-100
    overqualification_flag: bool
    irrelevant_experience_penalty: float  # 0-1
    experience_explanation: str


# Individual Candidate Score
class CandidateScore(BaseModel):
    """Scoring breakdown for a single candidate"""
    skills_score: float  # 0-100
    experience_score: float  # 0-100
    role_alignment_score: float  # 0-100
    education_score: float  # 0-100
    weighted_total_score: float  # 0-100
    scoring_explanation: str


# Candidate Explanation
class CandidateExplanation(BaseModel):
    """Detailed explanation for a candidate's ranking"""
    rank_position: int
    overall_match_score: float  # 0-100
    strengths: List[str]
    gaps: List[str]
    missing_requirements: List[str]
    risk_flags: List[str]
    reasoning: str  # Bullet-point reasoning


# Combined Analysis Result (single API call output)
class CombinedAnalysisResult(BaseModel):
    """Combined result from single LLM call - includes parsing, matching, evaluation, scoring"""
    # Resume parsing fields
    candidate_name: Optional[str] = None
    skills: List[str]
    experience: List[Dict[str, Any]]
    total_years_experience: float
    projects: Optional[List[Dict[str, Any]]] = None
    education: Optional[List[Dict[str, Any]]] = None
    certifications: Optional[List[str]] = None
    
    # Skill matching fields
    matched_mandatory_skills: List[str]
    matched_preferred_skills: List[str]
    missing_mandatory_skills: List[str]
    missing_preferred_skills: List[str]
    skill_match_score: float
    skill_explanation: str
    
    # Experience evaluation fields
    total_relevant_experience_years: float
    domain_relevance_score: float
    role_alignment_score: float
    overqualification_flag: bool
    irrelevant_experience_penalty: float
    experience_explanation: str
    
    # Scoring fields
    skills_score: float
    experience_score: float
    role_alignment_score: float
    education_score: float
    weighted_total_score: float
    
    # Explanation fields
    strengths: List[str]
    gaps: List[str]
    missing_requirements: List[str]
    risk_flags: List[str]
    reasoning: str


# Ranked Candidate Result
class RankedCandidate(BaseModel):
    """Final ranked candidate with all details"""
    candidate_name: Optional[str]
    rank: int
    overall_score: float  # 0-100
    score_breakdown: CandidateScore
    explanation: CandidateExplanation
    structured_resume: StructuredResume


# Final Summary
class ScreeningSummary(BaseModel):
    """Final summary of the screening process"""
    top_3_candidates: List[Dict[str, Any]]  # Simplified info for top 3
    common_gaps_observed: List[str]
    hiring_risks: List[str]
    overall_statistics: Dict[str, Any]  # e.g., {"total_candidates": 10, "avg_score": 65.5}


# Final Response
class ResumeScreeningResponse(BaseModel):
    """Complete response from resume screening"""
    ranked_candidates: List[RankedCandidate]
    summary: ScreeningSummary
    scoring_weights_used: Dict[str, float]
    processing_metadata: Optional[Dict[str, Any]] = None
