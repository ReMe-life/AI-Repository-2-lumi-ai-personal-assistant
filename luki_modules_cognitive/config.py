"""
Configuration for LUKi Cognitive Modules
"""
import os
from typing import Optional, List
from pydantic import BaseSettings, Field


class CognitiveConfig(BaseSettings):
    """Configuration for cognitive modules"""
    
    # Memory Service Integration
    memory_service_url: str = Field(
        default="http://localhost:8002",
        env="LUKI_MEMORY_SERVICE_URL",
        description="URL for LUKi memory service"
    )
    
    # Vector Store Configuration
    vector_store_type: str = Field(
        default="chromadb",
        env="COGNITIVE_VECTOR_STORE_TYPE",
        description="Type of vector store (chromadb, faiss)"
    )
    
    vector_store_path: str = Field(
        default="./data/vector_store",
        env="COGNITIVE_VECTOR_STORE_PATH",
        description="Path to vector store data"
    )
    
    # Embedding Model Configuration
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        env="COGNITIVE_EMBEDDING_MODEL",
        description="Sentence transformer model for embeddings"
    )
    
    # Activity Recommendation Settings
    max_recommendations: int = Field(
        default=5,
        env="COGNITIVE_MAX_RECOMMENDATIONS",
        description="Maximum number of activity recommendations to return"
    )
    
    recommendation_threshold: float = Field(
        default=0.7,
        env="COGNITIVE_RECOMMENDATION_THRESHOLD",
        description="Minimum similarity threshold for recommendations"
    )
    
    # ReMeLife Activity Integration
    rememades_enabled: bool = Field(
        default=True,
        env="COGNITIVE_REMEMADES_ENABLED",
        description="Enable ReMeMades (World Days) activities"
    )
    
    personal_activities_weight: float = Field(
        default=0.8,
        env="COGNITIVE_PERSONAL_WEIGHT",
        description="Weight for personal vs group activities"
    )
    
    # Personality Integration
    personality_framework_path: str = Field(
        default="../_context/10-LUKi-Personality-Framework.md",
        env="COGNITIVE_PERSONALITY_PATH",
        description="Path to LUKi personality framework"
    )
    
    # Analytics Configuration
    wellbeing_metrics_enabled: bool = Field(
        default=True,
        env="COGNITIVE_WELLBEING_METRICS",
        description="Enable wellbeing metrics calculation"
    )
    
    feedback_analysis_enabled: bool = Field(
        default=True,
        env="COGNITIVE_FEEDBACK_ANALYSIS",
        description="Enable NLP feedback analysis"
    )
    
    # Security & Privacy
    encrypt_vector_store: bool = Field(
        default=True,
        env="COGNITIVE_ENCRYPT_VECTORS",
        description="Encrypt vector store data"
    )
    
    respect_consent_flags: bool = Field(
        default=True,
        env="COGNITIVE_RESPECT_CONSENT",
        description="Respect ELR consent flags"
    )
    
    # Logging
    log_level: str = Field(
        default="INFO",
        env="COGNITIVE_LOG_LEVEL",
        description="Logging level"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global config instance
config = CognitiveConfig()


def get_config() -> CognitiveConfig:
    """Get the global configuration instance"""
    return config
