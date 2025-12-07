"""
FastAPI application for LUKi Cognitive Modules
"""

import os
import asyncio
import hashlib
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging

import httpx
from together import Together

from .config import CognitiveConfig
from .recommender.recommend import ActivityRecommender
from .data.activity_catalog import ActivityCatalog
from .interfaces.agent_tools import CognitiveTools, COGNITIVE_TOOL_DEFINITIONS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

config = CognitiveConfig()
logger.info(
    "CognitiveConfig loaded | security_service_url=%s",
    config.security_service_url,
)
TOGETHER_FLUX_MODEL = "black-forest-labs/FLUX.1-dev"
PHOTO_RATE_WINDOW_SECONDS = 3600
PHOTO_MAX_IMAGES_PER_MEMORY = 5
PHOTO_MAX_MEMORIES_PER_USER = 3
_photo_rate_state: Dict[str, Any] = {
    "per_memory": {},
    "per_user": {},
}

# Initialize FastAPI app
app = FastAPI(
    title="LUKi Cognitive Modules",
    description="Personalised activity creation, cognitive stimulation & wellbeing analytics",
    version="0.1.0"
)

def _consent_checks_enabled() -> bool:
    """Return True if consent/policy checks should be applied for secondary uses."""
    return bool(getattr(config, "respect_consent_flags", True))


def _build_photo_reminiscence_prompt(
    activity_title: Optional[str], answers: List[str]
) -> str:
    parts: List[str] = []
    title = (activity_title or "").strip()
    if title:
        parts.append(
            f'A warm, realistic photograph inspired by the activity "{title}".'
        )
    else:
        parts.append(
            "A warm, realistic photograph inspired by a meaningful personal memory."
        )
    non_empty = [a.strip() for a in answers if a and a.strip()]
    for index, text in enumerate(non_empty, start=1):
        parts.append(f"Detail {index}: {text}")
    parts.append(
        "Style: gentle nostalgic tone, natural lighting, soft focus, no text, no watermarks."
    )
    return " ".join(parts)


def _compute_photo_memory_id(
    activity_title: Optional[str], answers: List[str]
) -> str:
    base_parts: List[str] = []
    title = (activity_title or "").strip()
    if title:
        base_parts.append(title)
    for value in answers:
        if value and value.strip():
            base_parts.append(value.strip())
    if not base_parts:
        return "default"
    raw = "||".join(base_parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _photo_rate_check(user_id: str, memory_id: str, now: datetime) -> Optional[Dict[str, Any]]:
    window = timedelta(seconds=PHOTO_RATE_WINDOW_SECONDS)
    state = _photo_rate_state
    per_memory = state["per_memory"]
    per_user = state["per_user"]
    mem_key = f"{user_id}:{memory_id}"
    mem_entry = per_memory.get(mem_key)
    if mem_entry is not None:
        start = mem_entry.get("window_start")
        if isinstance(start, datetime) and now - start >= window:
            mem_entry["window_start"] = now
            mem_entry["count"] = 0
    else:
        mem_entry = {"window_start": now, "count": 0}
        per_memory[mem_key] = mem_entry
    user_entry = per_user.get(user_id)
    if user_entry is not None:
        start = user_entry.get("window_start")
        if isinstance(start, datetime) and now - start >= window:
            user_entry["window_start"] = now
            user_entry["memory_ids"] = set()
    else:
        user_entry = {"window_start": now, "memory_ids": set()}
        per_user[user_id] = user_entry
    if mem_entry.get("count", 0) >= PHOTO_MAX_IMAGES_PER_MEMORY:
        return {
            "status": "rate_limited",
            "scope": "per_memory",
            "message": "Image limit reached for this memory. Please try again later.",
        }
    memory_ids = user_entry.get("memory_ids") or set()
    is_new_memory = memory_id not in memory_ids
    if is_new_memory and len(memory_ids) >= PHOTO_MAX_MEMORIES_PER_USER:
        return {
            "status": "rate_limited",
            "scope": "per_user",
            "message": "Image limit reached for now. Please try again later.",
        }
    return None


def _photo_rate_record(
    user_id: str,
    memory_id: str,
    now: datetime,
    image_count: int,
) -> None:
    if image_count <= 0:
        return
    window = timedelta(seconds=PHOTO_RATE_WINDOW_SECONDS)
    state = _photo_rate_state
    per_memory = state["per_memory"]
    per_user = state["per_user"]
    mem_key = f"{user_id}:{memory_id}"
    mem_entry = per_memory.get(mem_key)
    if mem_entry is None or not isinstance(mem_entry.get("window_start"), datetime) or now - mem_entry["window_start"] >= window:
        mem_entry = {"window_start": now, "count": 0}
        per_memory[mem_key] = mem_entry
    mem_entry["count"] = int(mem_entry.get("count", 0)) + image_count
    user_entry = per_user.get(user_id)
    if user_entry is None or not isinstance(user_entry.get("window_start"), datetime) or now - user_entry["window_start"] >= window:
        user_entry = {"window_start": now, "memory_ids": set()}
        per_user[user_id] = user_entry
    memory_ids = user_entry.get("memory_ids")
    if not isinstance(memory_ids, set):
        memory_ids = set()
        user_entry["memory_ids"] = memory_ids
    memory_ids.add(memory_id)


async def _enforce_cognitive_policy(
    user_id: str,
    requested_scopes: Optional[List[str]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Call security service policy/enforce for cognitive recommendations.

    Defaults to requesting personalization scope. When consent
    checks are disabled via configuration, this returns allowed=True without
    making an external call.
    """
    if not _consent_checks_enabled():
        return {"allowed": True, "reason": "consent_checks_disabled"}

    scopes = requested_scopes or ["personalization"]

    payload: Dict[str, Any] = {
        "user_id": user_id,
        "requester_role": "cognitive_service",
        "requested_scopes": scopes,
    }
    if context:
        payload["context"] = context

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{config.security_service_url}/policy/enforce",
                json=payload,
            )

        try:
            raw = response.json()
        except ValueError:
            raw = {"detail": response.text}

        if isinstance(raw, dict):
            data: Dict[str, Any] = raw
        else:
            data = {"detail": raw}

        if response.status_code == 200:
            return {
                "allowed": bool(data.get("allowed", True)),
                "scopes_checked": data.get("scopes_checked", []),
                "reason": data.get("reason", "consent_valid"),
                "detail": data.get("detail"),
            }

        return {
            "allowed": False,
            "error": data.get("error", "policy_denied"),
            "detail": data.get("detail"),
            "status_code": response.status_code,
        }
    except Exception as exc:  # pragma: no cover - defensive guard
        # IMPORTANT: activity recommendations are a core experience and
        # should not be permanently blocked just because the security
        # service is temporarily unreachable or misconfigured. In these
        # cases we *fail open* for the personalization scope and allow
        # the request, while still logging the failure for operators.
        logger.error(
            "Cognitive policy enforcement request failed for user %s: %s",
            user_id,
            str(exc),
        )
        return {
            "allowed": True,
            "reason": "policy_request_failed_default_allow_personalization",
            "detail": str(exc),
        }


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


class GeneratedImage(BaseModel):
    id: str
    prompt: str
    b64_json: str
    width: Optional[int] = None
    height: Optional[int] = None
    model: Optional[str] = None


class PhotoReminiscenceImageRequest(BaseModel):
    user_id: str
    activity_title: Optional[str] = None
    answers: List[str]
    n: Optional[int] = 1


class PhotoReminiscenceImageResponse(BaseModel):
    status: str
    images: List[GeneratedImage]


# Life Story Recording models
class LifeStoryStartRequest(BaseModel):
    user_id: str


class LifeStoryContinueRequest(BaseModel):
    user_id: str
    session_id: str
    response_text: str
    skip_phase: bool = False
    approximate_date: Optional[str] = None


class LifeStorySessionsRequest(BaseModel):
    user_id: str
    include_chunks: bool = False


class LifeStoryDeleteRequest(BaseModel):
    user_id: str
    session_id: str


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
        "version": "0.2.0",
        "status": "running",
        "endpoints": [
            "/health",
            "/recommendations",
            "/activities",
            "/world-day-activities/{user_id}",
            "/images/photo-reminiscence",
            "/life-story/start",
            "/life-story/continue",
            "/life-story/sessions/{user_id}",
            "/life-story/phases",
            "/tools",
        ]
    }

# Activity recommendations endpoint
@app.post("/recommendations", response_model=RecommendationResponse)
async def get_recommendations(request: RecommendationRequest):
    """Get personalized activity recommendations"""
    if not cognitive_tools:
        raise HTTPException(status_code=503, detail="Cognitive tools not available")
    
    try:
        policy = await _enforce_cognitive_policy(
            user_id=request.user_id,
            context={
                "endpoint": "recommendations",
                "max_recommendations": request.max_recommendations,
            },
        )
        if not policy.get("allowed", True):
            logger.info(
                "Cognitive recommendations blocked by policy for user %s: %s",
                request.user_id,
                policy.get("error"),
            )
            raise HTTPException(
                status_code=403,
                detail={
                    "error": policy.get("error", "consent_denied"),
                    "policy": policy,
                },
            )

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
        activities = []
        for activity in activity_catalog.activities.values():
            activities.append({
                "id": activity.id,
                "title": activity.title,
                "description": activity.description,
                "category": activity.activity_type.value,
                "type": activity.activity_type.value,
                "module": activity.module.value,
                "cognitive_level": [level.value for level in activity.cognitive_level],
                "tags": activity.tags,
                "duration_minutes": activity.duration_minutes,
                "requires_carer": activity.requires_carer,
                "supports_group": activity.supports_group,
                "world_day_theme": activity.world_day_theme,
                "content_type": activity.content_type,
            })
        
        return {"activities": activities}
    except Exception as e:
        logger.error(f"Error fetching activities: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch activities")

# World day activities endpoint
@app.get("/world-day-activities/{user_id}")
async def get_world_day_activities(user_id: str):
    """Get today's world day activities (ReMeMades) for a user"""
    if not cognitive_tools:
        raise HTTPException(status_code=503, detail="Cognitive tools not available")

    try:
        policy = await _enforce_cognitive_policy(
            user_id=user_id,
            context={"endpoint": "world-day-activities"},
        )
        if not policy.get("allowed", True):
            logger.info(
                "World day activities blocked by policy for user %s: %s",
                user_id,
                policy.get("error"),
            )
            raise HTTPException(
                status_code=403,
                detail={
                    "error": policy.get("error", "consent_denied"),
                    "policy": policy,
                },
            )

        result = await cognitive_tools.get_world_day_activities(user_id)
        if not result.get("success"):
            logger.error(f"Error fetching world day activities: {result.get('error')}")
            raise HTTPException(status_code=500, detail="Failed to fetch world day activities")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching world day activities: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch world day activities")


@app.post("/images/photo-reminiscence", response_model=PhotoReminiscenceImageResponse)
async def generate_photo_reminiscence_images(
    request: PhotoReminiscenceImageRequest,
):
    if not request.answers:
        raise HTTPException(status_code=400, detail="At least one answer is required")
    try:
        memory_id = _compute_photo_memory_id(request.activity_title, request.answers)
        now = datetime.utcnow()
        rate_error = _photo_rate_check(request.user_id, memory_id, now)
        if rate_error:
            raise HTTPException(status_code=429, detail=rate_error)
        prompt = _build_photo_reminiscence_prompt(request.activity_title, request.answers)
        n = request.n or 1
        if n < 1:
            n = 1
        if n > 4:
            n = 4

        def _call_together() -> List[Dict[str, Any]]:
            client = Together()
            logger.info(
                "PhotoReminiscence: calling Together images.generate | model=%s, n=%s",
                TOGETHER_FLUX_MODEL,
                n,
            )
            logger.info("PhotoReminiscence: prompt (first 400 chars): %s", prompt[:400])
            result = client.images.generate(
                prompt=prompt,
                model=TOGETHER_FLUX_MODEL,
                steps=10,
                n=n,
                response_format="b64_json",
            )
            images: List[Dict[str, Any]] = []
            data = getattr(result, "data", None) or []
            logger.info(
                "PhotoReminiscence: Together result type=%s, data_len=%d",
                type(result).__name__,
                len(data),
            )
            for index, item in enumerate(data):
                if isinstance(item, dict):
                    b64 = item.get("b64_json")
                    img_prompt = item.get("prompt", prompt)
                    width = item.get("width")
                    height = item.get("height")
                    model_name = item.get("model", TOGETHER_FLUX_MODEL)
                else:
                    b64 = getattr(item, "b64_json", None)
                    img_prompt = getattr(item, "prompt", prompt)
                    width = getattr(item, "width", None)
                    height = getattr(item, "height", None)
                    model_name = getattr(item, "model", TOGETHER_FLUX_MODEL)
                if not b64:
                    # Introspect structure so we can see what fields Together is returning
                    try:
                        if isinstance(item, dict):
                            keys = list(item.keys())
                        elif hasattr(item, "model_dump"):
                            # Pydantic model from Together SDK
                            keys = list(item.model_dump().keys())
                        else:
                            keys = [
                                attr
                                for attr in dir(item)
                                if not attr.startswith("_") and not callable(getattr(item, attr, None))
                            ]
                        logger.warning(
                            "PhotoReminiscence: skipping image index=%d because b64_json missing; type=%s; keys=%s",
                            index,
                            type(item).__name__,
                            keys,
                        )
                    except Exception as introspect_err:
                        logger.warning(
                            "PhotoReminiscence: failed to introspect image index=%d type=%s: %s",
                            index,
                            type(item).__name__,
                            introspect_err,
                        )
                    continue
                images.append(
                    {
                        "id": f"img_{index}",
                        "prompt": img_prompt,
                        "b64_json": b64,
                        "width": width,
                        "height": height,
                        "model": model_name,
                    }
                )
            return images

        images = await asyncio.to_thread(_call_together)
        if not images:
            raise HTTPException(
                status_code=502, detail="Image generation returned no results"
            )
        _photo_rate_record(request.user_id, memory_id, datetime.utcnow(), len(images))
        parsed_images = [GeneratedImage(**item) for item in images]
        return PhotoReminiscenceImageResponse(status="ok", images=parsed_images)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating photo reminiscence images: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate images")

# ==================== LIFE STORY RECORDING ENDPOINTS ====================

@app.post("/life-story/start")
async def start_life_story(request: LifeStoryStartRequest):
    """Start a new life story recording session"""
    if not cognitive_tools:
        raise HTTPException(status_code=503, detail="Cognitive tools not available")
    
    try:
        # Enforce policy for life story (high sensitivity data)
        policy = await _enforce_cognitive_policy(
            user_id=request.user_id,
            context={
                "endpoint": "life-story-start",
                "sensitivity": "high",
            },
        )
        if not policy.get("allowed", True):
            logger.info(
                "Life story recording blocked by policy for user %s: %s",
                request.user_id,
                policy.get("error"),
            )
            raise HTTPException(
                status_code=403,
                detail={
                    "error": policy.get("error", "consent_denied"),
                    "policy": policy,
                },
            )
        
        result = await cognitive_tools.start_life_story_session(request.user_id)
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to start session"))
        
        # Log without sensitive data
        logger.info(
            "Life story session started: user_id=%s, session_id=%s, resumed=%s",
            request.user_id[:8] + "...",  # Truncate for privacy
            result.get("session_id", "")[:8] + "...",
            result.get("resumed", False),
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting life story session: {e}")
        raise HTTPException(status_code=500, detail="Failed to start life story session")


@app.post("/life-story/continue")
async def continue_life_story(request: LifeStoryContinueRequest):
    """Continue a life story session with a new response"""
    if not cognitive_tools:
        raise HTTPException(status_code=503, detail="Cognitive tools not available")
    
    try:
        # Enforce policy
        policy = await _enforce_cognitive_policy(
            user_id=request.user_id,
            context={
                "endpoint": "life-story-continue",
                "sensitivity": "high",
                "session_id": request.session_id,
            },
        )
        if not policy.get("allowed", True):
            raise HTTPException(
                status_code=403,
                detail={
                    "error": policy.get("error", "consent_denied"),
                    "policy": policy,
                },
            )
        
        result = await cognitive_tools.continue_life_story_session(
            user_id=request.user_id,
            session_id=request.session_id,
            response_text=request.response_text,
            skip_phase=request.skip_phase,
            approximate_date=request.approximate_date,
        )
        
        if not result.get("success"):
            error = result.get("error", "Failed to continue session")
            if error == "session_not_found":
                raise HTTPException(status_code=404, detail="Session not found")
            raise HTTPException(status_code=500, detail=error)
        
        # Log without sensitive content
        logger.info(
            "Life story chunk recorded: session_id=%s, phase=%s, completed=%s",
            request.session_id[:8] + "...",
            result.get("current_phase", "unknown"),
            result.get("completed", False),
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error continuing life story session: {e}")
        raise HTTPException(status_code=500, detail="Failed to continue life story session")


@app.get("/life-story/sessions/{user_id}")
async def get_life_story_sessions(user_id: str, include_chunks: bool = False):
    """Get all life story sessions for a user"""
    if not cognitive_tools:
        raise HTTPException(status_code=503, detail="Cognitive tools not available")
    
    try:
        # Enforce policy
        policy = await _enforce_cognitive_policy(
            user_id=user_id,
            context={
                "endpoint": "life-story-sessions",
                "sensitivity": "high",
            },
        )
        if not policy.get("allowed", True):
            raise HTTPException(
                status_code=403,
                detail={
                    "error": policy.get("error", "consent_denied"),
                    "policy": policy,
                },
            )
        
        result = await cognitive_tools.get_life_story_sessions(
            user_id=user_id,
            include_chunks=include_chunks,
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching life story sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch life story sessions")


@app.delete("/life-story/sessions/{session_id}")
async def delete_life_story_session(session_id: str, user_id: str):
    """Delete a life story session"""
    if not cognitive_tools:
        raise HTTPException(status_code=503, detail="Cognitive tools not available")
    
    try:
        # Enforce policy
        policy = await _enforce_cognitive_policy(
            user_id=user_id,
            context={
                "endpoint": "life-story-delete",
                "sensitivity": "high",
                "session_id": session_id,
            },
        )
        if not policy.get("allowed", True):
            raise HTTPException(
                status_code=403,
                detail={
                    "error": policy.get("error", "consent_denied"),
                    "policy": policy,
                },
            )
        
        result = await cognitive_tools.delete_life_story_session(
            user_id=user_id,
            session_id=session_id,
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to delete session"))
        
        logger.info(
            "Life story session deleted: session_id=%s",
            session_id[:8] + "...",
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting life story session: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete life story session")


@app.get("/life-story/phases")
async def get_life_story_phases():
    """Get all available life story phases and their prompts"""
    from .data.life_story import PHASE_ORDER, PHASE_PROMPTS
    
    phases = []
    for i, phase in enumerate(PHASE_ORDER):
        config = PHASE_PROMPTS.get(phase, {})
        phases.append({
            "phase": phase.value,
            "index": i,
            "prompt": config.get("prompt", ""),
            "follow_ups": config.get("follow_ups", []),
            "skip_allowed": config.get("skip_allowed", True),
        })
    
    return {
        "phases": phases,
        "total_phases": len(phases),
    }


# Cognitive tools endpoint
@app.get("/tools")
async def get_cognitive_tools():
    """Get available cognitive tools"""
    if not cognitive_tools:
        raise HTTPException(status_code=503, detail="Cognitive tools not available")
    
    try:
        # This is a placeholder - implement actual tools logic
        tools = []
        for tool_def in COGNITIVE_TOOL_DEFINITIONS:
            tools.append({
                "name": tool_def.get("name"),
                "description": tool_def.get("description"),
                "parameters": tool_def.get("parameters"),
            })
        
        return {
            "tools": tools,
            "total_tools": len(tools),
        }
    except Exception as e:
        logger.error(f"Error fetching cognitive tools: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch cognitive tools")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
