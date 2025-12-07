"""
Life Story Recording Data Models and Adapter

Provides structured storage for guided life story recording sessions.
Each session captures memories across life phases with high-sensitivity
ELR tagging for privacy-first handling.
"""
import uuid
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import httpx

from ..config import get_config


class LifeStoryPhase(str, Enum):
    """Phases of life story recording journey"""
    INTRODUCTION = "introduction"
    CHILDHOOD = "childhood"
    EDUCATION = "education"
    WORK_CAREER = "work_career"
    RELATIONSHIPS = "relationships"
    ACHIEVEMENTS = "achievements"
    CHALLENGES = "challenges"
    SPECIAL_MEMORIES = "special_memories"
    SUMMARY = "summary"


# Phase order for guided journey
PHASE_ORDER = [
    LifeStoryPhase.INTRODUCTION,
    LifeStoryPhase.CHILDHOOD,
    LifeStoryPhase.EDUCATION,
    LifeStoryPhase.WORK_CAREER,
    LifeStoryPhase.RELATIONSHIPS,
    LifeStoryPhase.ACHIEVEMENTS,
    LifeStoryPhase.CHALLENGES,
    LifeStoryPhase.SPECIAL_MEMORIES,
    LifeStoryPhase.SUMMARY,
]


# Warm, comfortable prompts for each phase
PHASE_PROMPTS: Dict[LifeStoryPhase, Dict[str, Any]] = {
    LifeStoryPhase.INTRODUCTION: {
        "prompt": "Let's capture some of your life story together. We'll go through different chapters of your life at your own pace. There's no rush — share as much or as little as feels comfortable. Ready to begin?",
        "follow_up": "Wonderful! Let's start with your earliest memories.",
        "skip_allowed": False,
    },
    LifeStoryPhase.CHILDHOOD: {
        "prompt": "Tell me about your childhood. Where did you grow up? What was your home like?",
        "follow_ups": [
            "What's a happy memory from when you were young?",
            "Did you have any favourite games or activities as a child?",
            "Who was someone special to you growing up?",
        ],
        "skip_allowed": True,
    },
    LifeStoryPhase.EDUCATION: {
        "prompt": "What was school like for you? Any favourite subjects or teachers you remember?",
        "follow_ups": [
            "Did you enjoy learning? What interested you most?",
            "Any school friends you remember fondly?",
        ],
        "skip_allowed": True,
    },
    LifeStoryPhase.WORK_CAREER: {
        "prompt": "Tell me about your working life. What kind of work did you do?",
        "follow_ups": [
            "What did you enjoy most about your work?",
            "Any colleagues who became good friends?",
            "What's something you were proud of achieving at work?",
        ],
        "skip_allowed": True,
    },
    LifeStoryPhase.RELATIONSHIPS: {
        "prompt": "Let's talk about the important people in your life. Tell me about your family or close friends.",
        "follow_ups": [
            "Is there someone who has been especially important to you?",
            "What's a favourite memory with someone you love?",
        ],
        "skip_allowed": True,
    },
    LifeStoryPhase.ACHIEVEMENTS: {
        "prompt": "What are you most proud of in your life? It doesn't have to be big — sometimes the small things matter most.",
        "follow_ups": [
            "Is there something you accomplished that surprised even yourself?",
            "What would you want others to remember about you?",
        ],
        "skip_allowed": True,
    },
    LifeStoryPhase.CHALLENGES: {
        "prompt": "Life has its ups and downs. Is there a challenge you faced that you're comfortable sharing? How did you get through it?",
        "follow_ups": [
            "What helped you during difficult times?",
            "Did you learn something important from that experience?",
        ],
        "skip_allowed": True,
    },
    LifeStoryPhase.SPECIAL_MEMORIES: {
        "prompt": "Is there any other special memory or story you'd like to share? Something that means a lot to you?",
        "follow_ups": [
            "A place that was special to you?",
            "A tradition or celebration you loved?",
            "Something that always makes you smile when you think of it?",
        ],
        "skip_allowed": True,
    },
    LifeStoryPhase.SUMMARY: {
        "prompt": "Thank you so much for sharing your story with me. It's been wonderful learning about your life. Would you like to add anything else before we finish?",
        "follow_up": "Your story has been saved. You can always come back to add more or look back at what you've shared.",
        "skip_allowed": False,
    },
}


@dataclass
class LifeStoryChunk:
    """A single chunk/entry in a life story session"""
    chunk_id: str
    session_id: str
    user_id: str
    phase: LifeStoryPhase
    prompt_used: str
    response: str
    approximate_date: Optional[str] = None  # e.g., "1960s", "childhood", "age 25"
    themes: List[str] = field(default_factory=list)
    people_mentioned: List[str] = field(default_factory=list)
    places_mentioned: List[str] = field(default_factory=list)
    media_ids: List[str] = field(default_factory=list)  # For future media attachments
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "chunk_id": self.chunk_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "phase": self.phase.value,
            "prompt_used": self.prompt_used,
            "response": self.response,
            "approximate_date": self.approximate_date,
            "themes": self.themes,
            "people_mentioned": self.people_mentioned,
            "places_mentioned": self.places_mentioned,
            "media_ids": self.media_ids,
            "timestamp": self.timestamp.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LifeStoryChunk":
        """Create from dictionary"""
        return cls(
            chunk_id=data["chunk_id"],
            session_id=data["session_id"],
            user_id=data["user_id"],
            phase=LifeStoryPhase(data["phase"]),
            prompt_used=data["prompt_used"],
            response=data["response"],
            approximate_date=data.get("approximate_date"),
            themes=data.get("themes", []),
            people_mentioned=data.get("people_mentioned", []),
            places_mentioned=data.get("places_mentioned", []),
            media_ids=data.get("media_ids", []),
            timestamp=datetime.fromisoformat(data["timestamp"]) if isinstance(data.get("timestamp"), str) else data.get("timestamp", datetime.utcnow()),
        )


@dataclass
class LifeStorySession:
    """A complete life story recording session"""
    session_id: str
    user_id: str
    status: str  # "in_progress", "completed", "abandoned"
    current_phase: LifeStoryPhase
    current_phase_index: int
    chunks: List[LifeStoryChunk] = field(default_factory=list)
    summary: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    total_duration_minutes: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "status": self.status,
            "current_phase": self.current_phase.value,
            "current_phase_index": self.current_phase_index,
            "chunks": [chunk.to_dict() for chunk in self.chunks],
            "summary": self.summary,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_duration_minutes": self.total_duration_minutes,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LifeStorySession":
        """Create from dictionary"""
        chunks = [LifeStoryChunk.from_dict(c) for c in data.get("chunks", [])]
        return cls(
            session_id=data["session_id"],
            user_id=data["user_id"],
            status=data["status"],
            current_phase=LifeStoryPhase(data["current_phase"]),
            current_phase_index=data.get("current_phase_index", 0),
            chunks=chunks,
            summary=data.get("summary"),
            started_at=datetime.fromisoformat(data["started_at"]) if isinstance(data.get("started_at"), str) else data.get("started_at", datetime.utcnow()),
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            total_duration_minutes=data.get("total_duration_minutes"),
        )


class LifeStoryAdapter:
    """Adapter for storing and retrieving life story data via Memory Service"""
    
    SENSITIVITY_LEVEL = "high"  # Life story data is high sensitivity
    CONTENT_TYPE = "life_story"
    
    def __init__(self):
        self.config = get_config()
        self.memory_service_url = self.config.memory_service_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
    
    async def create_session(self, user_id: str) -> LifeStorySession:
        """Create a new life story recording session"""
        session = LifeStorySession(
            session_id=str(uuid.uuid4()),
            user_id=user_id,
            status="in_progress",
            current_phase=PHASE_ORDER[0],
            current_phase_index=0,
        )
        
        await self._save_session(session)
        return session
    
    async def get_session(self, session_id: str, user_id: str) -> Optional[LifeStorySession]:
        """Retrieve an existing session"""
        try:
            response = await self.client.get(
                f"{self.memory_service_url}/v1/kv/get",
                params={"user_id": user_id, "key": f"life_story_session:{session_id}"}
            )
            
            if response.status_code == 200:
                data = response.json().get("value")
                if data:
                    return LifeStorySession.from_dict(data)
            return None
        except Exception as e:
            print(f"Error retrieving life story session: {e}")
            return None
    
    async def get_active_session(self, user_id: str) -> Optional[LifeStorySession]:
        """Get user's currently active (in-progress) session if any"""
        sessions = await self.get_user_sessions(user_id)
        for session in sessions:
            if session.status == "in_progress":
                return session
        return None
    
    async def get_user_sessions(self, user_id: str) -> List[LifeStorySession]:
        """Get all life story sessions for a user"""
        try:
            response = await self.client.get(
                f"{self.memory_service_url}/v1/kv/get",
                params={"user_id": user_id, "key": "life_story_sessions_index"}
            )
            
            if response.status_code == 200:
                session_ids = response.json().get("value", [])
                sessions = []
                for sid in session_ids:
                    session = await self.get_session(sid, user_id)
                    if session:
                        sessions.append(session)
                return sorted(sessions, key=lambda s: s.started_at, reverse=True)
            return []
        except Exception as e:
            print(f"Error retrieving user sessions: {e}")
            return []
    
    async def add_chunk(
        self,
        session: LifeStorySession,
        response_text: str,
        approximate_date: Optional[str] = None,
        themes: Optional[List[str]] = None,
    ) -> LifeStoryChunk:
        """Add a new chunk to the session and save"""
        phase_config = PHASE_PROMPTS.get(session.current_phase, {})
        prompt_used = phase_config.get("prompt", "")
        
        chunk = LifeStoryChunk(
            chunk_id=str(uuid.uuid4()),
            session_id=session.session_id,
            user_id=session.user_id,
            phase=session.current_phase,
            prompt_used=prompt_used,
            response=response_text,
            approximate_date=approximate_date,
            themes=themes or [],
        )
        
        session.chunks.append(chunk)
        
        # Also store chunk as individual ELR entry for searchability
        await self._store_chunk_as_elr(chunk)
        
        # Save updated session
        await self._save_session(session)
        
        return chunk
    
    async def advance_phase(self, session: LifeStorySession) -> Optional[LifeStoryPhase]:
        """Advance to next phase, return new phase or None if complete"""
        next_index = session.current_phase_index + 1
        
        if next_index >= len(PHASE_ORDER):
            return None
        
        session.current_phase_index = next_index
        session.current_phase = PHASE_ORDER[next_index]
        await self._save_session(session)
        
        return session.current_phase
    
    async def complete_session(
        self,
        session: LifeStorySession,
        summary: Optional[str] = None,
    ) -> LifeStorySession:
        """Mark session as completed and generate summary"""
        session.status = "completed"
        session.completed_at = datetime.utcnow()
        
        if session.started_at:
            duration = session.completed_at - session.started_at
            session.total_duration_minutes = int(duration.total_seconds() / 60)
        
        # Generate summary if not provided
        if summary:
            session.summary = summary
        else:
            session.summary = self._generate_session_summary(session)
        
        # Store summary as separate ELR entry
        await self._store_session_summary_as_elr(session)
        
        await self._save_session(session)
        return session
    
    async def delete_session(self, session_id: str, user_id: str) -> bool:
        """Delete a life story session and its chunks"""
        try:
            # Remove session from index
            response = await self.client.get(
                f"{self.memory_service_url}/v1/kv/get",
                params={"user_id": user_id, "key": "life_story_sessions_index"}
            )
            
            if response.status_code == 200:
                session_ids = response.json().get("value", [])
                if session_id in session_ids:
                    session_ids.remove(session_id)
                    await self.client.post(
                        f"{self.memory_service_url}/v1/kv/set",
                        json={
                            "user_id": user_id,
                            "key": "life_story_sessions_index",
                            "value": session_ids
                        }
                    )
            
            # Delete session data
            await self.client.post(
                f"{self.memory_service_url}/v1/kv/delete",
                json={
                    "user_id": user_id,
                    "key": f"life_story_session:{session_id}"
                }
            )
            
            return True
        except Exception as e:
            print(f"Error deleting session: {e}")
            return False
    
    async def _save_session(self, session: LifeStorySession) -> bool:
        """Save session to memory service"""
        try:
            # Save session data
            response = await self.client.post(
                f"{self.memory_service_url}/v1/kv/set",
                json={
                    "user_id": session.user_id,
                    "key": f"life_story_session:{session.session_id}",
                    "value": session.to_dict()
                }
            )
            
            if response.status_code != 200:
                return False
            
            # Update sessions index
            index_response = await self.client.get(
                f"{self.memory_service_url}/v1/kv/get",
                params={"user_id": session.user_id, "key": "life_story_sessions_index"}
            )
            
            session_ids = []
            if index_response.status_code == 200:
                session_ids = index_response.json().get("value", [])
            
            if session.session_id not in session_ids:
                session_ids.append(session.session_id)
                await self.client.post(
                    f"{self.memory_service_url}/v1/kv/set",
                    json={
                        "user_id": session.user_id,
                        "key": "life_story_sessions_index",
                        "value": session_ids
                    }
                )
            
            return True
        except Exception as e:
            print(f"Error saving session: {e}")
            return False
    
    async def _store_chunk_as_elr(self, chunk: LifeStoryChunk) -> bool:
        """Store chunk as individual ELR memory entry"""
        try:
            # Create ELR-compatible memory entry
            memory_data = {
                "user_id": chunk.user_id,
                "content": chunk.response,
                "content_type": self.CONTENT_TYPE,
                "sensitivity": self.SENSITIVITY_LEVEL,
                "metadata": {
                    "source": "life_story_recording",
                    "session_id": chunk.session_id,
                    "chunk_id": chunk.chunk_id,
                    "phase": chunk.phase.value,
                    "approximate_date": chunk.approximate_date,
                    "themes": chunk.themes,
                    "people_mentioned": chunk.people_mentioned,
                    "places_mentioned": chunk.places_mentioned,
                    "media_ids": chunk.media_ids,
                }
            }
            
            response = await self.client.post(
                f"{self.memory_service_url}/memories/ingest",
                json=memory_data
            )
            
            return response.status_code == 200
        except Exception as e:
            print(f"Error storing chunk as ELR: {e}")
            return False
    
    async def _store_session_summary_as_elr(self, session: LifeStorySession) -> bool:
        """Store session summary as ELR entry"""
        if not session.summary:
            return False
        
        try:
            memory_data = {
                "user_id": session.user_id,
                "content": session.summary,
                "content_type": f"{self.CONTENT_TYPE}_summary",
                "sensitivity": self.SENSITIVITY_LEVEL,
                "metadata": {
                    "source": "life_story_recording",
                    "session_id": session.session_id,
                    "is_summary": True,
                    "phases_completed": [c.phase.value for c in session.chunks],
                    "total_chunks": len(session.chunks),
                    "duration_minutes": session.total_duration_minutes,
                }
            }
            
            response = await self.client.post(
                f"{self.memory_service_url}/memories/ingest",
                json=memory_data
            )
            
            return response.status_code == 200
        except Exception as e:
            print(f"Error storing session summary as ELR: {e}")
            return False
    
    def _generate_session_summary(self, session: LifeStorySession) -> str:
        """Generate a brief summary of the life story session"""
        if not session.chunks:
            return "Life story session with no recorded memories."
        
        phases_covered = list(set(c.phase.value for c in session.chunks))
        chunk_count = len(session.chunks)
        
        summary_parts = [
            f"Life story recording session covering {len(phases_covered)} life phases",
            f"with {chunk_count} memories shared.",
        ]
        
        # Add brief mention of phases
        phase_names = {
            "childhood": "childhood memories",
            "education": "education experiences",
            "work_career": "career journey",
            "relationships": "important relationships",
            "achievements": "proud achievements",
            "challenges": "life challenges",
            "special_memories": "special moments",
        }
        
        covered_names = [phase_names.get(p, p) for p in phases_covered if p in phase_names]
        if covered_names:
            summary_parts.append(f"Includes {', '.join(covered_names[:3])}.")
        
        return " ".join(summary_parts)
    
    def get_phase_prompt(self, phase: LifeStoryPhase) -> Dict[str, Any]:
        """Get the prompt configuration for a phase"""
        return PHASE_PROMPTS.get(phase, {
            "prompt": "Tell me more about your life.",
            "skip_allowed": True,
        })
    
    def get_next_phase(self, current_phase: LifeStoryPhase) -> Optional[LifeStoryPhase]:
        """Get the next phase in the journey"""
        try:
            current_index = PHASE_ORDER.index(current_phase)
            if current_index + 1 < len(PHASE_ORDER):
                return PHASE_ORDER[current_index + 1]
        except ValueError:
            pass
        return None
