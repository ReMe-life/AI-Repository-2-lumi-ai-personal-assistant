"""
FastAPI application for LUKi Cognitive Modules
"""

import os
import asyncio
import hashlib
import base64
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
TOGETHER_FLUX_MODEL = "black-forest-labs/FLUX.1-schnell"
TOGETHER_FLUX_FALLBACK_MODEL = "black-forest-labs/FLUX.1-dev"
PHOTO_RATE_WINDOW_SECONDS = 21600  # 6 hours

# Tier-based image generation limits per 6-hour window
ACCOUNT_TIER_IMAGE_LIMITS: Dict[str, int] = {
    "free": 10,
    "plus": 50,
    "pro": 200,
}
PHOTO_MAX_IMAGES_PER_MEMORY = 10  # Max images per single memory per 6 hours (shared across tiers)

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


def _photo_rate_check(
    user_id: str, memory_id: str, now: datetime, account_tier: str = "free"
) -> Optional[Dict[str, Any]]:
    """Check if user has exceeded their tier-based image generation limit.
    
    Args:
        user_id: The user's ID
        memory_id: Hash of the memory/activity being generated
        now: Current datetime
        account_tier: User's subscription tier (free, plus, pro)
    
    Returns:
        None if within limits, or a rate_limited dict if exceeded
    """
    window = timedelta(seconds=PHOTO_RATE_WINDOW_SECONDS)
    state = _photo_rate_state
    per_memory = state["per_memory"]
    per_user = state["per_user"]
    
    # Get tier-based limit (default to free if unknown tier)
    user_limit = ACCOUNT_TIER_IMAGE_LIMITS.get(account_tier, ACCOUNT_TIER_IMAGE_LIMITS["free"])
    
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
            user_entry["total_images"] = 0
    else:
        user_entry = {"window_start": now, "total_images": 0}
        per_user[user_id] = user_entry
    
    # Check per-memory limit (prevents spamming regenerate on same memory)
    if mem_entry.get("count", 0) >= PHOTO_MAX_IMAGES_PER_MEMORY:
        return {
            "status": "rate_limited",
            "scope": "per_memory",
            "message": "Image limit reached for this memory. Please try again later.",
        }
    
    # Check tier-based total image limit
    current_total = user_entry.get("total_images", 0)
    if current_total >= user_limit:
        tier_display = account_tier.capitalize() if account_tier != "free" else "Free"
        return {
            "status": "rate_limited",
            "scope": "per_user",
            "message": f"You've reached your {tier_display} plan limit of {user_limit} images per 6 hours. Please try again later or upgrade your plan.",
            "limit": user_limit,
            "used": current_total,
            "remaining": 0,
            "tier": account_tier,
            "reset_window_seconds": PHOTO_RATE_WINDOW_SECONDS,
        }
    
    return None


def _get_photo_usage(user_id: str, account_tier: str = "free") -> Dict[str, Any]:
    """Get current image usage for a user.
    
    Returns:
        Dict with used, limit, tier, remaining
    """
    tier = account_tier.lower() if account_tier else "free"
    user_limit = ACCOUNT_TIER_IMAGE_LIMITS.get(tier, ACCOUNT_TIER_IMAGE_LIMITS["free"])
    
    state = _photo_rate_state
    per_user = state["per_user"]
    user_entry = per_user.get(user_id)
    
    now = datetime.utcnow()
    window = timedelta(seconds=PHOTO_RATE_WINDOW_SECONDS)
    
    if user_entry is not None:
        start = user_entry.get("window_start")
        if isinstance(start, datetime) and now - start >= window:
            # Window expired, reset
            used = 0
        else:
            used = user_entry.get("total_images", 0)
    else:
        used = 0
    
    return {
        "used": used,
        "limit": user_limit,
        "tier": tier,
        "remaining": max(0, user_limit - used),
        "reset_window_seconds": PHOTO_RATE_WINDOW_SECONDS,
    }


def _photo_rate_record(
    user_id: str,
    memory_id: str,
    now: datetime,
    image_count: int,
) -> None:
    """Record successful image generation for rate limiting tracking."""
    if image_count <= 0:
        return
    window = timedelta(seconds=PHOTO_RATE_WINDOW_SECONDS)
    state = _photo_rate_state
    per_memory = state["per_memory"]
    per_user = state["per_user"]
    
    # Update per-memory count
    mem_key = f"{user_id}:{memory_id}"
    mem_entry = per_memory.get(mem_key)
    if mem_entry is None or not isinstance(mem_entry.get("window_start"), datetime) or now - mem_entry["window_start"] >= window:
        mem_entry = {"window_start": now, "count": 0}
        per_memory[mem_key] = mem_entry
    mem_entry["count"] = int(mem_entry.get("count", 0)) + image_count
    
    # Update per-user total images count
    user_entry = per_user.get(user_id)
    if user_entry is None or not isinstance(user_entry.get("window_start"), datetime) or now - user_entry["window_start"] >= window:
        user_entry = {"window_start": now, "total_images": 0}
        per_user[user_id] = user_entry
    user_entry["total_images"] = int(user_entry.get("total_images", 0)) + image_count


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
    account_tier: Optional[str] = "free"  # free, plus, pro - determines image generation limits


class ImageUsageInfo(BaseModel):
    """Usage info for image generation rate limiting."""
    used: int
    limit: int
    tier: str
    remaining: int
    reset_window_seconds: int = PHOTO_RATE_WINDOW_SECONDS


class PhotoReminiscenceImageResponse(BaseModel):
    status: str
    images: List[GeneratedImage]
    usage: Optional[ImageUsageInfo] = None

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
        account_tier = (request.account_tier or "free").lower()
        rate_error = _photo_rate_check(request.user_id, memory_id, now, account_tier)
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
            models_to_try = [TOGETHER_FLUX_MODEL, TOGETHER_FLUX_FALLBACK_MODEL]
            result = None
            last_error = None
            
            for model in models_to_try:
                try:
                    logger.info(
                        "PhotoReminiscence: calling Together images.generate | model=%s, n=%s",
                        model,
                        n,
                    )
                    logger.info("PhotoReminiscence: prompt (first 400 chars): %s", prompt[:400])
                    result = client.images.generate(
                        prompt=prompt,
                        model=model,
                        n=n,
                    )
                    # If we got here, the call succeeded
                    logger.info("PhotoReminiscence: Successfully generated with model=%s", model)
                    break
                except Exception as model_err:
                    last_error = model_err
                    logger.warning(
                        "PhotoReminiscence: model %s failed with error: %s. Trying next model...",
                        model,
                        str(model_err)[:200]
                    )
                    continue
            
            if result is None:
                logger.error("PhotoReminiscence: All models failed. Last error: %s", last_error)
                raise last_error or Exception("All image generation models failed")
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
                    url = item.get("url")
                    img_prompt = item.get("prompt", prompt)
                    width = item.get("width")
                    height = item.get("height")
                    model_name = item.get("model", TOGETHER_FLUX_MODEL)
                else:
                    b64 = getattr(item, "b64_json", None)
                    url = getattr(item, "url", None)
                    img_prompt = getattr(item, "prompt", prompt)
                    width = getattr(item, "width", None)
                    height = getattr(item, "height", None)
                    model_name = getattr(item, "model", TOGETHER_FLUX_MODEL)
                
                # Handle URL response by fetching and converting to base64
                if not b64 and url:
                    try:
                        with httpx.Client(timeout=30.0) as http_client:
                            img_response = http_client.get(url)
                            img_response.raise_for_status()
                            b64 = base64.b64encode(img_response.content).decode('utf-8')
                        logger.info("PhotoReminiscence: converted URL to b64 for index=%d", index)
                    except Exception as fetch_err:
                        logger.warning("PhotoReminiscence: failed to fetch URL for index=%d: %s", index, fetch_err)
                
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
        
        # Get updated usage info after recording the new images
        usage_data = _get_photo_usage(request.user_id, account_tier)
        usage_info = ImageUsageInfo(**usage_data)
        
        return PhotoReminiscenceImageResponse(status="ok", images=parsed_images, usage=usage_info)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating photo reminiscence images: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate images")

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

# ==================== LIFE STORY ENDPOINTS ====================

class StartLifeStoryRequest(BaseModel):
    """Request to start a life story session"""
    user_id: str

class ContinueLifeStoryRequest(BaseModel):
    """Request to continue a life story session"""
    user_id: str
    session_id: str
    response_text: Optional[str] = None
    skip_phase: bool = False
    approximate_date: Optional[str] = None

@app.post("/life-story/start")
async def start_life_story(request: StartLifeStoryRequest):
    """Start or resume a life story recording session"""
    if not cognitive_tools:
        raise HTTPException(status_code=503, detail="Cognitive tools not available")
    
    try:
        result = await cognitive_tools.start_life_story_session(request.user_id)
        return result
    except Exception as e:
        logger.error(f"Error starting life story session: {e}")
        raise HTTPException(status_code=500, detail="Failed to start life story session")

@app.post("/life-story/continue")
async def continue_life_story(request: ContinueLifeStoryRequest):
    """Continue a life story recording session with a new response"""
    if not cognitive_tools:
        raise HTTPException(status_code=503, detail="Cognitive tools not available")
    
    try:
        result = await cognitive_tools.continue_life_story_session(
            user_id=request.user_id,
            session_id=request.session_id,
            response_text=request.response_text,
            skip_phase=request.skip_phase,
            approximate_date=request.approximate_date,
        )
        return result
    except Exception as e:
        logger.error(f"Error continuing life story session: {e}")
        raise HTTPException(status_code=500, detail="Failed to continue life story session")

class FinishLifeStoryRequest(BaseModel):
    user_id: str
    session_id: str

@app.post("/life-story/finish-early")
async def finish_life_story_early(request: FinishLifeStoryRequest):
    """Finish a life story session early, saving whatever chapters have been recorded"""
    if not cognitive_tools:
        raise HTTPException(status_code=503, detail="Cognitive tools not available")
    
    try:
        result = await cognitive_tools.finish_life_story_early(
            user_id=request.user_id,
            session_id=request.session_id,
        )
        return result
    except Exception as e:
        logger.error(f"Error finishing life story session early: {e}")
        raise HTTPException(status_code=500, detail="Failed to finish life story session")

@app.get("/life-story/sessions/{user_id}")
async def get_life_story_sessions(user_id: str, include_chunks: bool = False):
    """Get all life story sessions for a user"""
    if not cognitive_tools:
        raise HTTPException(status_code=503, detail="Cognitive tools not available")
    
    try:
        result = await cognitive_tools.get_life_story_sessions(
            user_id=user_id,
            include_chunks=include_chunks,
        )
        return result
    except Exception as e:
        logger.error(f"Error getting life story sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to get life story sessions")

@app.delete("/life-story/sessions/{session_id}")
async def delete_life_story_session(session_id: str, user_id: str):
    """Delete a life story session"""
    if not cognitive_tools:
        raise HTTPException(status_code=503, detail="Cognitive tools not available")
    
    try:
        result = await cognitive_tools.delete_life_story_session(
            user_id=user_id,
            session_id=session_id,
        )
        return result
    except Exception as e:
        logger.error(f"Error deleting life story session: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete life story session")

@app.get("/life-story/phases")
async def get_life_story_phases():
    """Get all available life story phases"""
    from .data.life_story import PHASE_ORDER, PHASE_PROMPTS
    
    phases = []
    for phase in PHASE_ORDER:
        config = PHASE_PROMPTS.get(phase, {})
        phases.append({
            "phase": phase.value,
            "prompt": config.get("prompt", ""),
            "skip_allowed": config.get("skip_allowed", True),
        })
    
    return {"phases": phases, "total_phases": len(phases)}


class UpdateLifeStoryImagesRequest(BaseModel):
    user_id: str
    session_id: str
    images: dict  # {chapter_index: base64_image_data}

@app.patch("/life-story/update-images")
async def update_life_story_images(request: UpdateLifeStoryImagesRequest):
    """
    Update a life story session with generated images.
    
    Saves image data for each chapter of a completed life story by updating
    the story_chunks metadata in the memory service.
    """
    if not cognitive_tools:
        raise HTTPException(status_code=503, detail="Cognitive tools not initialized")
    
    try:
        result = await cognitive_tools.life_story_adapter.update_session_images(
            user_id=request.user_id,
            session_id=request.session_id,
            images=request.images
        )
        return result
    except Exception as e:
        logger.error(f"Error updating life story images: {e}")
        raise HTTPException(status_code=500, detail="Failed to update life story images")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
