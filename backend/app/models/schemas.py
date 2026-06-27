"""
Pydantic Models for Talent Quest
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class JobDescription(BaseModel):
    """Job Description Schema"""
    title: str
    description: str
    required_skills: List[str]
    preferred_skills: Optional[List[str]] = []
    experience_years: int = Field(ge=0, description="Minimum years of experience")
    education_level: str = Field(..., description="Minimum education level required")
    location: str
    industry: str
    department: Optional[str] = None
    employment_type: Optional[str] = "Full-time"
    salary_range: Optional[Dict[str, int]] = None
    
class CandidateRanking(BaseModel):
    """Ranked Candidate Schema"""
    candidate_id: int
    name: str
    score: float = Field(ge=0, le=1, description="Final composite score")
    
    # Individual scores
    semantic_score: float = Field(ge=0, le=1)
    career_depth: float = Field(ge=0, le=2)
    skill_match: float = Field(ge=0, le=1)
    behavioral_score: float = Field(ge=0, le=1)
    location_fit: float = Field(ge=0, le=1)
    education_score: float = Field(ge=0, le=1)
    
    # Candidate details
    skills: str
    experience_years: int
    current_role: str
    education_level: str
    location: str
    
    # Additional metadata
    rank_position: Optional[int] = None
    matched_skills: Optional[List[str]] = None
    missing_skills: Optional[List[str]] = None
    
class RankingResponse(BaseModel):
    """Ranking API Response"""
    job_title: str
    total_candidates: int
    ranked_candidates: List[CandidateRanking]
    timestamp: datetime = Field(default_factory=datetime.now)
    pipeline_version: str = "1.0.0"
    
class PipelineMetrics(BaseModel):
    """Pipeline Performance Metrics"""
    total_time_seconds: float
    stages: Dict[str, float]
    candidates_processed: int
    candidates_ranked: int
    
class CandidateProfile(BaseModel):
    """Full Candidate Profile"""
    candidate_id: int
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    skills: List[str]
    experience: List[Dict[str, Any]]
    education: List[Dict[str, Any]]
    current_role: str
    location: str
    salary_expectation: Optional[int] = None
    availability: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
