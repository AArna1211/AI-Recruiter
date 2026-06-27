"""
Validation Utilities
"""
from typing import Dict, List, Any
import pandas as pd

def validate_jd(jd_data: Dict):
    """Validate job description data"""
    required_fields = ['title', 'description', 'required_skills', 'experience_years']
    
    for field in required_fields:
        if field not in jd_data:
            raise ValueError(f"Missing required field: {field}")
    
    if not jd_data['required_skills']:
        raise ValueError("At least one required skill is needed")
    
    if jd_data['experience_years'] < 0:
        raise ValueError("Experience years must be non-negative")
    
    return True

def validate_candidates(candidates: pd.DataFrame):
    """Validate candidate data"""
    required_columns = ['candidate_id', 'name', 'skills', 'experience_years']
    
    for col in required_columns:
        if col not in candidates.columns:
            raise ValueError(f"Missing required column: {col}")
    
    if candidates.empty:
        raise ValueError("No candidates provided")
    
    if candidates['candidate_id'].duplicated().any():
        raise ValueError("Duplicate candidate IDs found")
    
    return True

def validate_skills(skills: List[str]) -> bool:
    """Validate skills list"""
    if not skills:
        return False
    
    # Check for minimum skill count
    if len(skills) < 3:
        return False
    
    # Check for duplicates
    if len(skills) != len(set(skills)):
        return False
    
    return True
