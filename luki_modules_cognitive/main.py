"""
FastAPI application for LUKi Cognitive Modules
"""

import os
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging

from .config import CognitiveConfig
from .recommender.recommend import ActivityRecommender
from .data.activity_catalog import ActivityCatalog
from .interfaces.agent_tools import CognitiveTools

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize configuration
config = CognitiveConfig()

# Initialize FastAPI app
app = FastAPI(
    title="LUKi Cognitive Modules",
    description="Personalised activity creation, cognitive stimulation & wellbeing analytics",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
try:
    activity_recommender = ActivityRecommender()
    activity_catalog = ActivityCatalog()
    cognitive_tools = CognitiveTools()
    logger.info("Cognitive modules initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize cognitive modules: {e}")
    activity_recommender = None
    activity_catalog = None
    cognitive_tools = None

# Request/Response models
class RecommendationRequest(BaseModel):
    user_id: str
    preferences: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None
    max_recommendations: Optional[int] = 5
    current_mood: Optional[str] = None
    available_duration: Optional[int] = None
    carer_available: bool = True
    group_setting: bool = False
    specific_request: Optional[str] = None

class RecommendationResponse(BaseModel):
    recommendations: List[Dict[str, Any]]
    user_id: str
    timestamp: str

class HealthResponse(BaseModel):
    status: str
    version: str
    components: Dict[str, str]

# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for Railway deployment"""
    components = {
        "activity_recommender": "healthy" if activity_recommender else "error",
        "activity_catalog": "healthy" if activity_catalog else "error",
        "cognitive_tools": "healthy" if cognitive_tools else "error"
    }
    
    return HealthResponse(
        status="healthy" if all(status == "healthy" for status in components.values()) else "degraded",
        version="0.1.0",
        components=components
    )

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "LUKi Cognitive Modules",
        "version": "0.1.0",
        "status": "running",
        "endpoints": ["/health", "/recommendations", "/activities"]
    }

# Activity recommendations endpoint
@app.post("/recommendations", response_model=RecommendationResponse)
async def get_recommendations(request: RecommendationRequest):
    """Get personalized activity recommendations"""
    if not cognitive_tools:
        raise HTTPException(status_code=503, detail="Cognitive tools not available")
    
    try:
        context_data = request.context or {}
        current_mood = request.current_mood or context_data.get("current_mood")
        available_duration = request.available_duration or context_data.get("available_duration")
        specific_request = request.specific_request or context_data.get("specific_request")
        max_recommendations = request.max_recommendations or config.max_recommendations
        result = await cognitive_tools.recommend_activity(
            user_id=request.user_id,
            current_mood=current_mood,
            available_duration=available_duration,
            carer_available=request.carer_available,
            group_setting=request.group_setting,
            specific_request=specific_request,
            max_recommendations=max_recommendations,
        )
        if not result.get("success"):
            logger.error(f"Error generating recommendations: {result.get('error')}")
            raise HTTPException(status_code=500, detail="Failed to generate recommendations")
        recommendations = result.get("recommendations", [])
        return RecommendationResponse(
            recommendations=recommendations,
            user_id=request.user_id,
            timestamp=datetime.utcnow().isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate recommendations")

# Activity catalog endpoint
@app.get("/activities")
async def get_activities():
    """Get available activities from catalog"""
    if not activity_catalog:
        raise HTTPException(status_code=503, detail="Activity catalog not available")
    
    try:
        # This is a placeholder - implement actual catalog logic
        activities = [
            {
                "id": "activity_1",
                "title": "Morning Meditation",
                "category": "wellness",
                "tags": ["mindfulness", "morning", "relaxation"]
            }
        ]
        
        return {"activities": activities}
    except Exception as e:
        logger.error(f"Error fetching activities: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch activities")

# Cognitive tools endpoint
@app.get("/tools")
async def get_cognitive_tools():
    """Get available cognitive tools"""
    if not cognitive_tools:
        raise HTTPException(status_code=503, detail="Cognitive tools not available")
    
    try:
        # This is a placeholder - implement actual tools logic
        tools = [
            {
                "name": "memory_assessment",
                "description": "Assess memory capabilities",
                "category": "assessment"
            }
        ]
        
        return {"tools": tools}
    except Exception as e:
        logger.error(f"Error fetching cognitive tools: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch cognitive tools")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
