"""
Life Story Recording Data Models and Adapter

Provides structured storage for guided life story recording sessions.
Each session captures memories across life phases with high-sensitivity
ELR tagging for privacy-first handling.
"""
import uuid
import logging
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import httpx

from ..config import get_config

logger = logging.getLogger(__name__)


class LifeStoryPhase(str, Enum):
    """Phases of life story recording journey"""
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
    """Adapter for storing and retrieving life story data.
    
    Uses in-memory storage for active sessions and ELR ingestion for 
    permanent storage of completed chunks and summaries.
    """
    
    SENSITIVITY_LEVEL = "high"  # Life story data is high sensitivity
    CONTENT_TYPE = "life_story"
    
    # In-memory session storage (keyed by session_id)
    _sessions: Dict[str, LifeStorySession] = {}
    # Index of sessions per user (keyed by user_id -> list of session_ids)
    _user_sessions: Dict[str, List[str]] = {}
    
    def __init__(self):
        self.config = get_config()
        # Strip trailing slash to prevent double-slash in URL paths
        self.memory_service_url = self.config.memory_service_url.rstrip('/')
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
        
        # Store in memory
        self._sessions[session.session_id] = session
        
        # Update user index
        if user_id not in self._user_sessions:
            self._user_sessions[user_id] = []
        if session.session_id not in self._user_sessions[user_id]:
            self._user_sessions[user_id].append(session.session_id)
        
        return session
    
    async def get_session(self, session_id: str, user_id: str) -> Optional[LifeStorySession]:
        """Retrieve an existing session from memory"""
        session = self._sessions.get(session_id)
        if session and session.user_id == user_id:
            return session
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
        session_ids = self._user_sessions.get(user_id, [])
        sessions = []
        for sid in session_ids:
            session = self._sessions.get(sid)
            if session:
                sessions.append(session)
        return sorted(sessions, key=lambda s: s.started_at, reverse=True)
    
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
        
        # NOTE: We don't store individual chunks - only save ONE combined entry
        # when the session is completed via complete_session()
        
        # Save updated session in memory
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
        """Mark session as completed and store the complete life story"""
        logger.info(f"Completing Life Story session {session.session_id} for user {session.user_id} with {len(session.chunks)} chunks")
        session.status = "completed"
        session.completed_at = datetime.utcnow()
        
        if session.started_at:
            duration = session.completed_at - session.started_at
            session.total_duration_minutes = int(duration.total_seconds() / 60)
        
        # Generate a simple title/summary for display
        if summary:
            session.summary = summary
        else:
            session.summary = self._generate_session_title(session)
        
        # Store the COMPLETE story as ONE entry (all user responses)
        await self._store_complete_story_as_elr(session)
        
        await self._save_session(session)
        return session
    
    async def delete_session(self, session_id: str, user_id: str) -> bool:
        """Delete a life story session from memory"""
        try:
            # Remove from session storage
            if session_id in self._sessions:
                del self._sessions[session_id]
            
            # Remove from user index
            if user_id in self._user_sessions:
                if session_id in self._user_sessions[user_id]:
                    self._user_sessions[user_id].remove(session_id)
            
            return True
        except Exception as e:
            print(f"Error deleting session: {e}")
            return False
    
    async def _save_session(self, session: LifeStorySession) -> bool:
        """Save session to in-memory storage"""
        try:
            # Update session in memory
            self._sessions[session.session_id] = session
            
            # Ensure user index is updated
            if session.user_id not in self._user_sessions:
                self._user_sessions[session.user_id] = []
            if session.session_id not in self._user_sessions[session.user_id]:
                self._user_sessions[session.user_id].append(session.session_id)
            
            return True
        except Exception as e:
            print(f"Error saving session: {e}")
            return False
    
    async def _store_chunk_as_elr(self, chunk: LifeStoryChunk) -> bool:
        """Store chunk as individual ELR memory entry"""
        try:
            # Create ELR-compatible memory entry matching ELRIngestionRequest schema
            # IMPORTANT: ChromaDB metadata can only store str, int, float, bool - NOT lists or None!
            # Convert lists to JSON strings and handle None values
            import json
            
            memory_data = {
                "user_id": chunk.user_id,
                "elr_data": {
                    "content": chunk.response,
                    "content_type": "MEMORY",  # Use valid ELRContentType
                    "timestamp": chunk.timestamp.isoformat() if chunk.timestamp else datetime.utcnow().isoformat(),
                    "metadata": {
                        "source": "life_story_recording",
                        "is_life_story": True,
                        "life_story_type": self.CONTENT_TYPE,
                        "session_id": chunk.session_id,
                        "chunk_id": chunk.chunk_id,
                        "phase": chunk.phase.value,
                        "approximate_date": chunk.approximate_date or "",
                        # Convert lists to JSON strings for ChromaDB compatibility
                        "themes": json.dumps(chunk.themes) if chunk.themes else "[]",
                        "people_mentioned": json.dumps(chunk.people_mentioned) if chunk.people_mentioned else "[]",
                        "places_mentioned": json.dumps(chunk.places_mentioned) if chunk.places_mentioned else "[]",
                        "media_ids": json.dumps(chunk.media_ids) if chunk.media_ids else "[]",
                    }
                },
                "source_file": "life_story_recording",
                "sensitivity_level": "sensitive",  # Life story data is sensitive
                "consent_level": "private"
            }
            
            response = await self.client.post(
                f"{self.memory_service_url}/ingestion/elr",
                json=memory_data
            )
            
            if response.status_code != 200:
                logger.error(f"ELR chunk storage failed with status {response.status_code}: {response.text}")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error storing chunk as ELR: {e}", exc_info=True)
            # Don't fail the session if ELR storage fails
            return False
    
    async def _store_complete_story_as_elr(self, session: LifeStorySession) -> bool:
        """Store the complete life story as a single ELR entry with all user responses"""
        if not session.chunks:
            return False
        
        try:
            import json
            
            # Build the complete story from all chunks - user's actual responses only
            story_content = self._build_complete_story(session)
            
            # Create ELR-compatible memory entry
            # IMPORTANT: ChromaDB metadata can only store str, int, float, bool - NOT lists or None!
            memory_data = {
                "user_id": session.user_id,
                "elr_data": {
                    "content": story_content,
                    "content_type": "MEMORY",
                    "timestamp": session.completed_at.isoformat() if session.completed_at else session.started_at.isoformat(),
                    "metadata": {
                        "source": "life_story_recording",
                        "life_story_type": self.CONTENT_TYPE,
                        "session_id": session.session_id,
                        "is_life_story": True,
                        # Store individual chunks as JSON for full story display
                        "story_chunks": json.dumps([
                            {
                                "phase": c.phase.value,
                                "response": c.response,
                                "approximate_date": c.approximate_date or ""
                            } for c in session.chunks
                        ]),
                        "phases_completed": json.dumps([c.phase.value for c in session.chunks]),
                        "total_chapters": len(session.chunks),
                        "duration_minutes": session.total_duration_minutes or 0,
                    }
                },
                "source_file": "life_story_complete",
                "sensitivity_level": "sensitive",
                "consent_level": "private"
            }
            
            logger.info(f"Storing Life Story to ELR for user {session.user_id}, session {session.session_id}")
            logger.debug(f"Memory data: {memory_data}")
            
            response = await self.client.post(
                f"{self.memory_service_url}/ingestion/elr",
                json=memory_data
            )
            
            if response.status_code != 200:
                logger.error(f"ELR summary storage failed with status {response.status_code}: {response.text}")
                return False
            
            logger.info(f"Life Story successfully saved to ELR for user {session.user_id}")
            return True
        except Exception as e:
            logger.error(f"Error storing session summary as ELR: {e}", exc_info=True)
            # Don't fail if ELR storage fails
            return False
    
    def _generate_session_title(self, session: LifeStorySession) -> str:
        """Generate a simple title for the life story session"""
        if not session.chunks:
            return "My Life Story"
        
        # Use the date as part of the title
        date_str = session.started_at.strftime("%B %d, %Y") if session.started_at else "Today"
        return f"My Life Story - {date_str}"
    
    def _build_complete_story(self, session: LifeStorySession) -> str:
        """Build the complete life story from all chunks - user's actual responses"""
        if not session.chunks:
            return ""
        
        # Phase display names for chapter headers
        phase_titles = {
            "introduction": "Introduction",
            "childhood": "Childhood",
            "education": "Education",
            "work_career": "Career",
            "relationships": "Relationships",
            "achievements": "Achievements",
            "challenges": "Challenges",
            "special_memories": "Special Memories",
            "summary": "Closing Thoughts",
        }
        
        story_parts = []
        for chunk in session.chunks:
            phase_title = phase_titles.get(chunk.phase.value, chunk.phase.value.replace("_", " ").title())
            # Just the user's actual response - no headers in stored content
            # Headers will be added by the UI when displaying
            story_parts.append(chunk.response)
        
        # Join with paragraph breaks
        return "\n\n".join(story_parts)
    
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
    
    async def update_session_images(
        self, 
        user_id: str, 
        session_id: str, 
        images: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Update a life story session with generated images.
        
        Args:
            user_id: User ID who owns the session
            session_id: The life story session ID
            images: Dict mapping chapter index (as string) to base64 image data
        
        Returns:
            Success status and updated session info
        """
        import json
        
        # First, get the existing memory for this session
        try:
            # Search for the life story memory by session_id
            search_response = await self.client.post(
                f"{self.memory_service_url}/search/memories",
                json={
                    "user_id": user_id,
                    "query": f"life story session {session_id}",
                    "limit": 10,
                    "filters": {
                        "source": "life_story_recording",
                        "session_id": session_id
                    }
                }
            )
            
            if search_response.status_code != 200:
                print(f"Failed to find life story memory: {search_response.text}")
                return {"success": False, "message": "Could not find life story memory"}
            
            search_result = search_response.json()
            memories = search_result.get("results", [])
            
            if not memories:
                # Try a broader search
                print(f"No memories found for session {session_id}, trying broader search")
                return {"success": False, "message": "Life story memory not found"}
            
            # Find the memory with matching session_id
            target_memory = None
            for memory in memories:
                metadata = memory.get("metadata", {})
                if metadata.get("session_id") == session_id:
                    target_memory = memory
                    break
            
            if not target_memory:
                target_memory = memories[0]  # Use first result as fallback
            
            memory_id = target_memory.get("id")
            metadata = target_memory.get("metadata", {})
            
            # Parse existing story_chunks
            story_chunks_json = metadata.get("story_chunks", "[]")
            try:
                story_chunks = json.loads(story_chunks_json)
            except:
                story_chunks = []
            
            # Update chunks with image data
            for idx_str, image_data in images.items():
                idx = int(idx_str)
                if idx < len(story_chunks):
                    story_chunks[idx]["image_url"] = image_data
            
            # Update the memory with new story_chunks
            updated_metadata = {**metadata, "story_chunks": json.dumps(story_chunks)}
            
            update_response = await self.client.patch(
                f"{self.memory_service_url}/memories/{memory_id}",
                json={
                    "user_id": user_id,
                    "metadata": updated_metadata
                }
            )
            
            if update_response.status_code != 200:
                print(f"Failed to update memory: {update_response.text}")
                return {"success": False, "message": "Failed to update memory with images"}
            
            return {
                "success": True,
                "message": f"Updated {len(images)} chapter images",
                "memory_id": memory_id
            }
            
        except Exception as e:
            print(f"Error updating session images: {e}")
            return {"success": False, "message": str(e)}
