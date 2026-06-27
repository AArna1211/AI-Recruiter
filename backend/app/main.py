"""
Talent Quest - AI-Powered Recruitment Ranking System
Main FastAPI Application
"""
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict
import pandas as pd
import numpy as np
import json
import logging
from datetime import datetime

from .services.ranking_pipeline import RankingPipeline
from .models.schemas import CandidateRanking, JobDescription, RankingResponse
from .utils.validators import validate_jd, validate_candidates
from .utils.logger import setup_logger

# Setup logging
logger = setup_logger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Talent Quest API",
    description="AI-Powered Recruitment Ranking System",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize pipeline
pipeline = RankingPipeline()

class RankingRequest(BaseModel):
    job_description: Dict
    candidates_file: Optional[str] = None
    top_k: Optional[int] = 100

@app.get("/")
async def root():
    return {
        "message": "🏰 Welcome to Talent Quest!",
        "version": "1.0.0",
        "status": "running",
        "endpoints": [
            "/health",
            "/rank",
            "/upload-candidates",
            "/job-description/parse"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "qdrant": pipeline.check_qdrant_health(),
            "redis": pipeline.check_redis_health()
        }
    }

@app.post("/rank", response_model=List[CandidateRanking])
async def rank_candidates(request: RankingRequest):
    """
    Main ranking endpoint
    """
    try:
        logger.info("Received ranking request")
        
        # Validate job description
        validate_jd(request.job_description)
        jd = JobDescription(**request.job_description)
        
        # Load candidates
        if request.candidates_file:
            candidates = pd.read_csv(request.candidates_file)
        else:
            logger.info("No candidates file provided, using mock data")
            candidates = generate_mock_candidates()
        
        # Validate candidates
        validate_candidates(candidates)
        
        # Run pipeline
        logger.info(f"Ranking {len(candidates)} candidates")
        ranked = pipeline.rank_candidates(jd, candidates)
        
        # Return top K
        top_k = min(request.top_k or 100, len(ranked))
        logger.info(f"Returning top {top_k} candidates")
        return ranked[:top_k]
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Ranking error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/upload-candidates")
async def upload_candidates(file: UploadFile = File(...)):
    """
    Upload candidate CSV file
    """
    try:
        df = pd.read_csv(file.file)
        file_path = f"data/processed/candidates_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(file_path, index=False)
        return {
            "message": "File uploaded successfully",
            "file_path": file_path,
            "num_candidates": len(df),
            "columns": df.columns.tolist()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")

@app.post("/job-description/parse")
async def parse_job_description(text: str):
    """
    Parse raw JD text into structured format
    """
    try:
        parsed = pipeline.parse_jd_text(text)
        return JSONResponse(content=parsed)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def generate_mock_candidates():
    """Generate mock candidate data for testing"""
    np.random.seed(42)
    n = 1000
    
    skills_pool = ['Python', 'Java', 'C++', 'React', 'SQL', 'AWS', 'Docker', 
                   'ML', 'NLP', 'PyTorch', 'TensorFlow', 'Spark', 'Kubernetes']
    roles = ['Data Scientist', 'ML Engineer', 'Backend Dev', 'Frontend Dev', 
             'DevOps', 'Data Engineer', 'Full Stack']
    locations = ['Remote', 'New York', 'SF', 'Austin', 'London', 'Berlin']
    
    def generate_skills():
        return ', '.join(np.random.choice(skills_pool, 
                                          size=np.random.randint(3, 7), 
                                          replace=False))
    
    return pd.DataFrame({
        'candidate_id': range(n),
        'name': [f'Candidate_{i}' for i in range(n)],
        'skills': [generate_skills() for _ in range(n)],
        'experience_years': np.random.exponential(5, n).astype(int),
        'education_level': np.random.choice(['PhD', 'Masters', 'Bachelors', 'High School'], n),
        'location': np.random.choice(locations, n),
        'current_role': np.random.choice(roles, n),
        'salary_expectation': np.random.randint(60000, 250000, n)
    })
