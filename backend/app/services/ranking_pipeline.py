"""
Core Ranking Pipeline Implementation
"""
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Tuple, Optional
from sentence_transformers import SentenceTransformer
import torch
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from sklearn.preprocessing import StandardScaler
import xgboost as xgb
import json
import redis
import hashlib
from datetime import datetime
import logging

from ..models.schemas import JobDescription, CandidateRanking
from ..utils.cache import cache_result

logger = logging.getLogger(__name__)

class RankingPipeline:
    def __init__(self):
        """Initialize the ranking pipeline with all components"""
        logger.info("Initializing Ranking Pipeline...")
        
        # Initialize ML models
        self.embedder = SentenceTransformer('BAAI/bge-base-en-v1.5')
        self.scaler = StandardScaler()
        self.vector_size = 768  # BGE embedding size
        
        # Initialize Qdrant client
        self.qdrant_client = QdrantClient("localhost", port=6333)
        self._init_qdrant_collection()
        
        # Initialize Redis for caching
        self.redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        
        # Weight configuration
        self.weights = {
            'semantic': 0.35,
            'career_depth': 0.25,
            'behavioral': 0.20,
            'location_fit': 0.10,
            'education': 0.10
        }
        
        # XGBoost model (to be trained)
        self.xgb_model = None
        
        logger.info("Pipeline initialization complete!")
    
    def _init_qdrant_collection(self):
        """Initialize Qdrant collection if not exists"""
        try:
            collections = self.qdrant_client.get_collections()
            if 'candidates' not in [c.name for c in collections.collections]:
                self.qdrant_client.create_collection(
                    collection_name="candidates",
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                )
                logger.info("Created Qdrant collection: candidates")
            else:
                logger.info("Qdrant collection 'candidates' already exists")
        except Exception as e:
            logger.warning(f"Qdrant initialization warning: {e}")
    
    def check_qdrant_health(self) -> bool:
        """Check if Qdrant is healthy"""
        try:
            self.qdrant_client.get_collections()
            return True
        except:
            return False
    
    def check_redis_health(self) -> bool:
        """Check if Redis is healthy"""
        try:
            self.redis_client.ping()
            return True
        except:
            return False
    
    @cache_result(ttl=3600)  # Cache for 1 hour
    def embed_text(self, text: str) -> np.ndarray:
        """Generate embedding for text with caching"""
        return self.embedder.encode(text, normalize_embeddings=True)
    
    def parse_jd_text(self, text: str) -> Dict:
        """Parse raw JD text into structured format"""
        # Simple parsing - in production use NLP/NER
        lines = text.split('\n')
        parsed = {
            'title': lines[0].strip() if lines else '',
            'description': '\n'.join(lines[1:10]) if len(lines) > 1 else '',
            'required_skills': [],
            'preferred_skills': []
        }
        
        # Simple skill extraction (demo)
        skill_keywords = ['Python', 'Java', 'SQL', 'AWS', 'Docker', 'ML', 'NLP']
        for line in lines:
            for skill in skill_keywords:
                if skill.lower() in line.lower():
                    parsed['required_skills'].append(skill)
        
        return parsed
    
    def rank_candidates(self, jd: JobDescription, candidates: pd.DataFrame) -> List[CandidateRanking]:
        """Main ranking pipeline"""
        logger.info("🏰 Starting Talent Quest Ranking Pipeline...")
        
        # Stage 1: JD Parsing & Embedding
        logger.info("📝 Stage 1: Parsing Job Description...")
        jd_text = self._format_jd(jd)
        jd_embedding = self.embed_text(jd_text)
        
        # Stage 2: Semantic Search
        logger.info("🔍 Stage 2: Semantic Search in Qdrant...")
        candidate_embeddings = self._get_candidate_embeddings(candidates)
        
        # Compute semantic scores
        semantic_scores = self._compute_semantic_scores(jd_embedding, candidate_embeddings)
        candidates['semantic_score'] = semantic_scores
        
        # Filter to top candidates
        top_n = min(500, len(candidates))
        top_candidates = candidates.nlargest(top_n, 'semantic_score')
        
        # Stage 3: Feature Engineering
        logger.info(f"⚙️ Stage 3: Feature Engineering ({len(top_candidates)} candidates)...")
        features = self._engineer_features(top_candidates, jd)
        
        # Stage 4: Composite Scoring
        logger.info("🎯 Stage 4: Composite Scoring...")
        final_scores = self._compute_composite_score(features)
        top_candidates['final_score'] = final_scores
        
        # Stage 5: Final Ranking
        logger.info("🏆 Stage 5: Final Ranking & Output...")
        ranked = top_candidates.nlargest(100, 'final_score')
        
        # Honeypot detection
        ranked = self._detect_honeypot(ranked)
        
        # Format results
        return self._format_results(ranked, features)
    
    def _format_jd(self, jd: JobDescription) -> str:
        """Format JD for embedding"""
        parts = [
            f"Title: {jd.title}",
            f"Description: {jd.description}",
            f"Required Skills: {', '.join(jd.required_skills)}",
            f"Preferred Skills: {', '.join(jd.preferred_skills) if jd.preferred_skills else 'None'}",
            f"Experience: {jd.experience_years} years",
            f"Education: {jd.education_level}",
            f"Location: {jd.location}",
            f"Industry: {jd.industry}"
        ]
        return " ".join(parts)
    
    def _get_candidate_embeddings(self, candidates: pd.DataFrame) -> np.ndarray:
        """Get or compute candidate embeddings"""
        candidate_texts = []
        for _, row in candidates.iterrows():
            text = f"Skills: {row['skills']} Experience: {row['experience_years']} years Role: {row['current_role']}"
            candidate_texts.append(text)
        
        embeddings = self.embedder.encode(candidate_texts, normalize_embeddings=True)
        self._store_embeddings(candidates, embeddings)
        return embeddings
    
    def _store_embeddings(self, candidates: pd.DataFrame, embeddings: np.ndarray):
        """Store embeddings in Qdrant"""
        points = []
        for idx, row in candidates.iterrows():
            points.append(
                PointStruct(
                    id=int(row['candidate_id']),
                    vector=embeddings[idx].tolist(),
                    payload=row.to_dict()
                )
            )
        
        try:
            self.qdrant_client.upsert(
                collection_name="candidates",
                points=points
            )
        except Exception as e:
            logger.warning(f"Failed to store embeddings: {e}")
    
    def _compute_semantic_scores(self, jd_embedding: np.ndarray, candidate_embeddings: np.ndarray) -> np.ndarray:
        """Compute semantic similarity scores"""
        scores = np.dot(candidate_embeddings, jd_embedding)
        # Scale to 0-1 range
        scores = (scores + 1) / 2
        return scores
    
    def _engineer_features(self, candidates: pd.DataFrame, jd: JobDescription) -> pd.DataFrame:
        """Engineer features for ranking"""
        features = candidates.copy()
        
        # Career Depth Feature
        features['career_depth'] = np.minimum(features['experience_years'] / jd.experience_years, 2.0)
        
        # Skill Match Score
        skills_list = [set(skills.split(', ')) for skills in features['skills']]
        required_skills = set(jd.required_skills)
        features['skill_match'] = [
            len(skills.intersection(required_skills)) / max(len(required_skills), 1)
            for skills in skills_list
        ]
        
        # Education Score
        edu_levels = {'High School': 1, 'Bachelors': 2, 'Masters': 3, 'PhD': 4}
        features['education_score'] = features['education_level'].map(edu_levels) / 4
        
        # Location Fit
        features['location_fit'] = (features['location'] == jd.location).astype(int) * 0.5 + 0.5
        features['location_fit'] = np.clip(features['location_fit'], 0.5, 1.0)
        
        # Behavioral signals (mock - in production from actual data)
        features['behavioral_score'] = np.random.normal(0.7, 0.1, len(features))
        features['behavioral_score'] = np.clip(features['behavioral_score'], 0, 1)
        
        return features
    
    def _compute_composite_score(self, features: pd.DataFrame) -> np.ndarray:
        """Compute weighted composite score"""
        # Normalize semantic score to 0-1
        features['semantic_normalized'] = features['semantic_score'] / features['semantic_score'].max()
        
        # Weighted sum
        score = (
            features['semantic_normalized'] * self.weights['semantic'] +
            features['career_depth'] * self.weights['career_depth'] +
            features['behavioral_score'] * self.weights['behavioral'] +
            features['location_fit'] * self.weights['location_fit'] +
            features['education_score'] * self.weights['education']
        )
        
        return score
    
    def _detect_honeypot(self, candidates: pd.DataFrame) -> pd.DataFrame:
        """Detect and filter honeypot candidates"""
        # Simple honeypot detection
        keyword_stuffers = candidates[
            candidates['skills'].str.split(', ').str.len() > 15
        ]
        
        if len(keyword_stuffers) > 0:
            logger.warning(f"Detected {len(keyword_stuffers)} potential keyword stuffers")
        
        # Flag ghost candidates (no experience but high scores)
        ghost_candidates = candidates[
            (candidates['experience_years'] < 1) & 
            (candidates['semantic_score'] > 0.8)
        ]
        
        if len(ghost_candidates) > 0:
            logger.warning(f"Detected {len(ghost_candidates)} potential ghost candidates")
        
        # Apply penalty
        candidates.loc[keyword_stuffers.index, 'final_score'] *= 0.7
        candidates.loc[ghost_candidates.index, 'final_score'] *= 0.5
        
        return candidates
    
    def _format_results(self, candidates: pd.DataFrame, features: pd.DataFrame) -> List[CandidateRanking]:
        """Format results for API response"""
        results = []
        for _, row in candidates.iterrows():
            feat_row = features[features['candidate_id'] == row['candidate_id']].iloc[0]
            
            results.append(CandidateRanking(
                candidate_id=int(row['candidate_id']),
                name=row['name'],
                score=float(row['final_score']),
                semantic_score=float(feat_row['semantic_score']),
                career_depth=float(feat_row['career_depth']),
                skill_match=float(feat_row['skill_match']),
                behavioral_score=float(feat_row['behavioral_score']),
                location_fit=float(feat_row['location_fit']),
                education_score=float(feat_row['education_score']),
                skills=row['skills'],
                experience_years=int(row['experience_years']),
                current_role=row['current_role'],
                education_level=row['education_level'],
                location=row['location']
            ))
        
        return results
