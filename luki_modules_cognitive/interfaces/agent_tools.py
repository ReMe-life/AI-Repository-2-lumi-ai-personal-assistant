"""
Agent Tools Interface

Provides tools for LUKi Core Agent to interact with the cognitive modules.
These tools are registered with the agent's tool registry for conversation use.
"""
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

from ..recommender.recommend import ActivityRecommender, RecommendationContext, ActivityEngagement
from ..data.activity_catalog import ActivityCatalog, ActivityType, CognitiveLevel
from ..data.elr_adapter import ELRAdapter
from ..data.life_story import (
    LifeStoryAdapter,
    LifeStorySession,
    LifeStoryChunk,
    LifeStoryPhase,
    PHASE_PROMPTS,
    PHASE_ORDER,
)
from ..config import get_config


class CognitiveTools:
    """Tools for LUKi agent to access cognitive module functionality"""
    
    def __init__(self):
        self.config = get_config()
        self.recommender = ActivityRecommender()
        self.catalog = ActivityCatalog()
        self.elr_adapter = ELRAdapter()
        self.life_story_adapter = LifeStoryAdapter()
    
    async def close(self):
        """Close resources"""
        await self.recommender.close()
        await self.life_story_adapter.close()
    
    async def recommend_activity(self, 
                               user_id: str,
                               current_mood: Optional[str] = None,
                               available_duration: Optional[int] = None,
                               carer_available: bool = True,
                               group_setting: bool = False,
                               specific_request: Optional[str] = None,
                               max_recommendations: int = 3) -> Dict[str, Any]:
        """
        Get personalized activity recommendations for a user
        
        Args:
            user_id: User identifier
            current_mood: User's current mood (happy, sad, anxious, etc.)
            available_duration: Available time in minutes
            carer_available: Whether a carer is available to assist
            group_setting: Whether this is for a group activity
            specific_request: Specific activity request from user
            max_recommendations: Maximum number of recommendations
            
        Returns:
            Dictionary with recommendations and metadata
        """
        try:
            # Determine time of day
            current_hour = datetime.now().hour
            if 6 <= current_hour < 12:
                time_of_day = "morning"
            elif 12 <= current_hour < 17:
                time_of_day = "afternoon"
            elif 17 <= current_hour < 21:
                time_of_day = "evening"
            else:
                time_of_day = "night"
            
            # Create recommendation context
            context = RecommendationContext(
                user_id=user_id,
                current_mood=current_mood,
                time_of_day=time_of_day,
                available_duration=available_duration,
                carer_available=carer_available,
                group_setting=group_setting,
                specific_request=specific_request
            )
            
            # Get recommendations
            recommendations = await self.recommender.get_recommendations(context, max_recommendations)
            
            # Format for agent response
            formatted_recommendations = []
            for rec in recommendations:
                formatted_rec = {
                    'id': rec.activity.id,
                    'title': rec.activity.title,
                    'description': rec.activity.description,
                    'type': rec.activity.activity_type.value,
                    'duration_minutes': rec.activity.duration_minutes,
                    'score': round(rec.score, 2),
                    'reasoning': rec.reasoning,
                    'personalization_notes': rec.personalization_notes,
                    'adaptation_suggestions': rec.adaptation_suggestions,
                    'estimated_engagement': round(rec.estimated_engagement, 2)
                }
                formatted_recommendations.append(formatted_rec)
            
            return {
                'success': True,
                'recommendations': formatted_recommendations,
                'context': {
                    'user_id': user_id,
                    'time_of_day': time_of_day,
                    'mood': current_mood,
                    'group_setting': group_setting
                },
                'total_found': len(recommendations)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'recommendations': []
            }
    
    async def get_world_day_activities(self, user_id: str) -> Dict[str, Any]:
        """
        Get today's world day activities (ReMeMades)
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary with world day activities
        """
        try:
            recommendations = await self.recommender.get_world_day_recommendations(user_id)
            
            formatted_activities = []
            for rec in recommendations:
                formatted_activity = {
                    'id': rec.activity.id,
                    'title': rec.activity.title,
                    'description': rec.activity.description,
                    'world_day_theme': rec.activity.world_day_theme,
                    'duration_minutes': rec.activity.duration_minutes,
                    'score': round(rec.score, 2),
                    'reasoning': rec.reasoning
                }
                formatted_activities.append(formatted_activity)
            
            return {
                'success': True,
                'world_day_activities': formatted_activities,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'total_found': len(recommendations)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'world_day_activities': []
            }
    
    async def record_activity_engagement(self,
                                       user_id: str,
                                       activity_id: str,
                                       engagement_score: float,
                                       duration_minutes: int,
                                       completion_status: str = "completed",
                                       feedback: Optional[str] = None,
                                       mood_before: Optional[str] = None,
                                       mood_after: Optional[str] = None,
                                       carer_notes: Optional[str] = None) -> Dict[str, Any]:
        """
        Record user engagement with an activity
        
        Args:
            user_id: User identifier
            activity_id: Activity identifier
            engagement_score: Engagement score from 0.0 to 1.0
            duration_minutes: Actual duration spent on activity
            completion_status: completed, partial, or abandoned
            feedback: User or carer feedback
            mood_before: User's mood before activity
            mood_after: User's mood after activity
            carer_notes: Additional notes from carer
            
        Returns:
            Dictionary with success status
        """
        try:
            # Get activity details
            activity = self.catalog.get_activity(activity_id)
            if not activity:
                return {
                    'success': False,
                    'error': f'Activity {activity_id} not found'
                }
            
            # Create engagement record
            engagement = ActivityEngagement(
                user_id=user_id,
                activity_id=activity_id,
                activity_type=activity.activity_type.value,
                engagement_score=engagement_score,
                duration_minutes=duration_minutes,
                completion_status=completion_status,
                feedback=feedback,
                mood_before=mood_before,
                mood_after=mood_after,
                carer_notes=carer_notes,
                timestamp=datetime.utcnow()
            )
            
            # Record the engagement
            success = await self.recommender.record_activity_feedback(engagement)
            
            return {
                'success': success,
                'message': 'Activity engagement recorded successfully' if success else 'Failed to record engagement'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_user_activity_summary(self, user_id: str, days: int = 7) -> Dict[str, Any]:
        """
        Get summary of user's recent activity engagement
        
        Args:
            user_id: User identifier
            days: Number of days to look back
            
        Returns:
            Dictionary with activity summary
        """
        try:
            # Get recent activity history
            history = await self.elr_adapter.get_user_activity_history(user_id, days)
            
            if not history:
                return {
                    'success': True,
                    'summary': {
                        'total_activities': 0,
                        'average_engagement': 0.0,
                        'favorite_types': [],
                        'recent_activities': []
                    }
                }
            
            # Calculate summary statistics
            total_activities = len(history)
            average_engagement = sum(eng.engagement_score for eng in history) / total_activities
            
            # Find favorite activity types
            type_counts = {}
            type_scores = {}
            for eng in history:
                if eng.activity_type not in type_counts:
                    type_counts[eng.activity_type] = 0
                    type_scores[eng.activity_type] = []
                type_counts[eng.activity_type] += 1
                type_scores[eng.activity_type].append(eng.engagement_score)
            
            # Calculate average scores for each type
            favorite_types = []
            for activity_type, scores in type_scores.items():
                avg_score = sum(scores) / len(scores)
                favorite_types.append({
                    'type': activity_type,
                    'count': type_counts[activity_type],
                    'average_score': round(avg_score, 2)
                })
            
            # Sort by average score
            favorite_types.sort(key=lambda x: x['average_score'], reverse=True)
            
            # Format recent activities
            recent_activities = []
            for eng in history[:5]:  # Last 5 activities
                recent_activities.append({
                    'activity_id': eng.activity_id,
                    'type': eng.activity_type,
                    'engagement_score': round(eng.engagement_score, 2),
                    'duration_minutes': eng.duration_minutes,
                    'completion_status': eng.completion_status,
                    'timestamp': eng.timestamp.isoformat()
                })
            
            return {
                'success': True,
                'summary': {
                    'total_activities': total_activities,
                    'average_engagement': round(average_engagement, 2),
                    'favorite_types': favorite_types[:3],  # Top 3
                    'recent_activities': recent_activities,
                    'period_days': days
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'summary': {}
            }
    
    async def search_activities(self, 
                              query: str,
                              user_id: Optional[str] = None,
                              activity_type: Optional[str] = None,
                              max_results: int = 5) -> Dict[str, Any]:
        """
        Search for activities based on query
        
        Args:
            query: Search query
            user_id: Optional user ID for personalization
            activity_type: Optional activity type filter
            max_results: Maximum number of results
            
        Returns:
            Dictionary with search results
        """
        try:
            # Convert activity type string to enum if provided
            type_filter = None
            if activity_type:
                try:
                    type_filter = ActivityType(activity_type)
                except ValueError:
                    pass
            
            # Search activities
            results = self.catalog.search_activities(
                query=query,
                activity_type=type_filter
            )
            
            # Limit results
            results = results[:max_results]
            
            # Format results
            formatted_results = []
            for activity in results:
                formatted_activity = {
                    'id': activity.id,
                    'title': activity.title,
                    'description': activity.description,
                    'type': activity.activity_type.value,
                    'module': activity.module.value,
                    'duration_minutes': activity.duration_minutes,
                    'tags': activity.tags,
                    'requires_carer': activity.requires_carer,
                    'supports_group': activity.supports_group
                }
                formatted_results.append(formatted_activity)
            
            return {
                'success': True,
                'results': formatted_results,
                'query': query,
                'total_found': len(formatted_results)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'results': []
            }
    
    async def get_personalized_mystory_prompt(self, user_id: str) -> Dict[str, Any]:
        """
        Get a personalized My Story prompt based on user's ELR
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary with personalized prompt
        """
        try:
            # Get user's ELR profile
            profile = await self.elr_adapter.get_user_elr_profile(user_id)
            
            if not profile:
                return {
                    'success': True,
                    'prompt': "Tell me about a special memory from your life.",
                    'suggestions': ["A favorite family tradition", "A memorable trip", "A proud moment"]
                }
            
            # Generate personalized prompts based on interests and family context
            prompts = []
            suggestions = []
            
            # Interest-based prompts
            if profile.interests:
                for interest in profile.interests[:2]:
                    prompts.append(f"Tell me about a time when you enjoyed {interest}.")
                    suggestions.append(f"Your experience with {interest}")
            
            # Family-based prompts
            if profile.family_context:
                prompts.append("Share a favorite memory with your family.")
                suggestions.append("A special family moment")
            
            # Music-based prompts
            if profile.music_preferences:
                prompts.append("Tell me about a song that brings back memories.")
                suggestions.append("A meaningful song from your past")
            
            # Default if no specific interests
            if not prompts:
                prompts = [
                    "Tell me about a day that made you really happy.",
                    "Share a memory from when you were younger.",
                    "Tell me about someone who was important to you."
                ]
                suggestions = ["A happy day", "A childhood memory", "An important person"]
            
            # Select a random prompt
            import random
            selected_prompt = random.choice(prompts)
            
            return {
                'success': True,
                'prompt': selected_prompt,
                'suggestions': suggestions[:3],
                'personalized': len(profile.interests) > 0 or bool(profile.family_context)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'prompt': "Tell me about a special memory from your life."
            }

    # ==================== LIFE STORY RECORDING ====================
    
    async def start_life_story_session(self, user_id: str) -> Dict[str, Any]:
        """
        Start a new life story recording session for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary with session info and first prompt
        """
        try:
            # Check for existing active session
            active_session = await self.life_story_adapter.get_active_session(user_id)
            if active_session:
                # Resume existing session
                phase_config = self.life_story_adapter.get_phase_prompt(active_session.current_phase)
                return {
                    'success': True,
                    'session_id': active_session.session_id,
                    'resumed': True,
                    'current_phase': active_session.current_phase.value,
                    'phase_index': active_session.current_phase_index,
                    'total_phases': len(PHASE_ORDER),
                    'prompt': phase_config.get('prompt', ''),
                    'skip_allowed': phase_config.get('skip_allowed', True),
                    'chunks_recorded': len(active_session.chunks),
                    'message': "Welcome back! Let's continue where we left off."
                }
            
            # Create new session
            session = await self.life_story_adapter.create_session(user_id)
            phase_config = self.life_story_adapter.get_phase_prompt(session.current_phase)
            
            return {
                'success': True,
                'session_id': session.session_id,
                'resumed': False,
                'current_phase': session.current_phase.value,
                'phase_index': session.current_phase_index,
                'total_phases': len(PHASE_ORDER),
                'prompt': phase_config.get('prompt', ''),
                'skip_allowed': phase_config.get('skip_allowed', False),
                'message': "Let's begin capturing your life story."
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': "I had trouble starting the life story session. Please try again."
            }
    
    async def continue_life_story_session(
        self,
        user_id: str,
        session_id: str,
        response_text: Optional[str] = None,
        skip_phase: bool = False,
        approximate_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Continue a life story session by recording a response and advancing.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            response_text: User's response to the current prompt
            skip_phase: Whether to skip this phase without recording
            approximate_date: Optional date context (e.g., "1960s", "childhood")
            
        Returns:
            Dictionary with next prompt or completion status
        """
        try:
            session = await self.life_story_adapter.get_session(session_id, user_id)
            if not session:
                return {
                    'success': False,
                    'error': 'session_not_found',
                    'message': "I couldn't find that session. Would you like to start a new one?"
                }
            
            if session.status != "in_progress":
                return {
                    'success': False,
                    'error': 'session_completed',
                    'message': "This life story session is already complete."
                }
            
            # Record chunk unless skipping
            if not skip_phase and response_text and response_text.strip():
                await self.life_story_adapter.add_chunk(
                    session=session,
                    response_text=response_text.strip(),
                    approximate_date=approximate_date,
                )
            
            # Advance to next phase
            next_phase = await self.life_story_adapter.advance_phase(session)
            
            if next_phase is None or next_phase == LifeStoryPhase.SUMMARY:
                # Session complete - finalize
                completed_session = await self.life_story_adapter.complete_session(session)
                return {
                    'success': True,
                    'completed': True,
                    'session_id': session_id,
                    'summary': completed_session.summary,
                    'chunks_recorded': len(completed_session.chunks),
                    'duration_minutes': completed_session.total_duration_minutes,
                    'message': "Thank you so much for sharing your story with me. Your memories have been safely saved.",
                    'prompt': PHASE_PROMPTS[LifeStoryPhase.SUMMARY].get('follow_up', '')
                }
            
            # Get next phase prompt
            phase_config = self.life_story_adapter.get_phase_prompt(next_phase)
            
            return {
                'success': True,
                'completed': False,
                'session_id': session_id,
                'current_phase': next_phase.value,
                'phase_index': session.current_phase_index,
                'total_phases': len(PHASE_ORDER),
                'prompt': phase_config.get('prompt', ''),
                'follow_ups': phase_config.get('follow_ups', []),
                'skip_allowed': phase_config.get('skip_allowed', True),
                'chunks_recorded': len(session.chunks),
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': "I had trouble saving that. Let's try again."
            }
    
    async def finish_life_story_early(
        self,
        user_id: str,
        session_id: str,
    ) -> Dict[str, Any]:
        """
        Finish a life story session early, saving whatever chapters have been recorded.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            
        Returns:
            Dictionary with completion status
        """
        try:
            session = await self.life_story_adapter.get_session(session_id, user_id)
            if not session:
                return {
                    'success': False,
                    'error': 'session_not_found',
                    'message': "I couldn't find that session."
                }
            
            if session.status != "in_progress":
                return {
                    'success': False,
                    'error': 'session_already_completed',
                    'message': "This life story session is already complete."
                }
            
            if not session.chunks:
                return {
                    'success': False,
                    'error': 'no_chapters_recorded',
                    'message': "You haven't recorded any chapters yet. Please share at least one memory before finishing."
                }
            
            # Complete the session with whatever has been recorded
            completed_session = await self.life_story_adapter.complete_session(session)
            
            return {
                'success': True,
                'completed': True,
                'session_id': session_id,
                'summary': completed_session.summary,
                'chunks_recorded': len(completed_session.chunks),
                'duration_minutes': completed_session.total_duration_minutes,
                'message': f"Your life story with {len(completed_session.chunks)} chapter{'s' if len(completed_session.chunks) != 1 else ''} has been saved. Thank you for sharing!",
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': "I had trouble saving your story. Let's try again."
            }
    
    async def get_life_story_sessions(
        self,
        user_id: str,
        include_chunks: bool = False,
    ) -> Dict[str, Any]:
        """
        Get all life story sessions for a user.
        
        Args:
            user_id: User identifier
            include_chunks: Whether to include full chunk details
            
        Returns:
            Dictionary with list of sessions
        """
        try:
            sessions = await self.life_story_adapter.get_user_sessions(user_id)
            
            formatted_sessions = []
            for session in sessions:
                session_info = {
                    'session_id': session.session_id,
                    'status': session.status,
                    'started_at': session.started_at.isoformat(),
                    'completed_at': session.completed_at.isoformat() if session.completed_at else None,
                    'chunks_count': len(session.chunks),
                    'phases_covered': list(set(c.phase.value for c in session.chunks)),
                    'summary': session.summary,
                    'duration_minutes': session.total_duration_minutes,
                }
                
                if include_chunks:
                    session_info['chunks'] = [
                        {
                            'chunk_id': c.chunk_id,
                            'phase': c.phase.value,
                            'response_preview': c.response[:100] + '...' if len(c.response) > 100 else c.response,
                            'approximate_date': c.approximate_date,
                            'timestamp': c.timestamp.isoformat(),
                        }
                        for c in session.chunks
                    ]
                
                formatted_sessions.append(session_info)
            
            return {
                'success': True,
                'sessions': formatted_sessions,
                'total_sessions': len(formatted_sessions),
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'sessions': []
            }
    
    async def delete_life_story_session(
        self,
        user_id: str,
        session_id: str,
    ) -> Dict[str, Any]:
        """
        Delete a life story session.
        
        Args:
            user_id: User identifier
            session_id: Session to delete
            
        Returns:
            Dictionary with deletion status
        """
        try:
            success = await self.life_story_adapter.delete_session(session_id, user_id)
            
            if success:
                return {
                    'success': True,
                    'message': "Your life story session has been deleted."
                }
            else:
                return {
                    'success': False,
                    'error': 'deletion_failed',
                    'message': "I couldn't delete that session. Please try again."
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': "Something went wrong while deleting the session."
            }
    
    async def get_life_story_prompt_for_phase(
        self,
        phase: str,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get the prompt for a specific life story phase.
        Optionally personalized based on user's ELR.
        
        Args:
            phase: Phase name
            user_id: Optional user ID for personalization
            
        Returns:
            Dictionary with phase prompt info
        """
        try:
            phase_enum = LifeStoryPhase(phase)
            phase_config = self.life_story_adapter.get_phase_prompt(phase_enum)
            
            result = {
                'success': True,
                'phase': phase,
                'prompt': phase_config.get('prompt', ''),
                'follow_ups': phase_config.get('follow_ups', []),
                'skip_allowed': phase_config.get('skip_allowed', True),
            }
            
            # Optionally personalize based on ELR
            if user_id:
                profile = await self.elr_adapter.get_user_elr_profile(user_id)
                if profile and profile.interests:
                    # Add personalized follow-up based on interests
                    for interest in profile.interests[:2]:
                        personalized = f"Did {interest} play a role in this part of your life?"
                        if personalized not in result.get('follow_ups', []):
                            result.setdefault('follow_ups', []).append(personalized)
            
            return result
            
        except ValueError:
            return {
                'success': False,
                'error': 'invalid_phase',
                'message': f"Unknown phase: {phase}",
                'valid_phases': [p.value for p in LifeStoryPhase]
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


# Tool registration functions for LUKi agent
def get_cognitive_tools() -> CognitiveTools:
    """Get cognitive tools instance"""
    return CognitiveTools()


# Tool definitions for LangChain integration
COGNITIVE_TOOL_DEFINITIONS = [
    {
        "name": "recommend_activity",
        "description": "Get personalized activity recommendations for a user based on their ELR profile, current mood, and context",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "User identifier"},
                "current_mood": {"type": "string", "description": "User's current mood (happy, sad, anxious, etc.)", "enum": ["happy", "sad", "anxious", "energetic", "tired", "confused", "agitated", "calm"]},
                "available_duration": {"type": "integer", "description": "Available time in minutes"},
                "carer_available": {"type": "boolean", "description": "Whether a carer is available to assist"},
                "group_setting": {"type": "boolean", "description": "Whether this is for a group activity"},
                "specific_request": {"type": "string", "description": "Specific activity request from user"},
                "max_recommendations": {"type": "integer", "description": "Maximum number of recommendations", "default": 3}
            },
            "required": ["user_id"]
        }
    },
    {
        "name": "get_world_day_activities", 
        "description": "Get today's world day activities (ReMeMades) for special occasions and events",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "User identifier"}
            },
            "required": ["user_id"]
        }
    },
    {
        "name": "record_activity_engagement",
        "description": "Record user engagement with an activity for learning and improvement",
        "parameters": {
            "type": "object", 
            "properties": {
                "user_id": {"type": "string", "description": "User identifier"},
                "activity_id": {"type": "string", "description": "Activity identifier"},
                "engagement_score": {"type": "number", "description": "Engagement score from 0.0 to 1.0"},
                "duration_minutes": {"type": "integer", "description": "Actual duration spent on activity"},
                "completion_status": {"type": "string", "description": "Completion status", "enum": ["completed", "partial", "abandoned"]},
                "feedback": {"type": "string", "description": "User or carer feedback"},
                "mood_before": {"type": "string", "description": "User's mood before activity"},
                "mood_after": {"type": "string", "description": "User's mood after activity"},
                "carer_notes": {"type": "string", "description": "Additional notes from carer"}
            },
            "required": ["user_id", "activity_id", "engagement_score", "duration_minutes"]
        }
    },
    {
        "name": "search_activities",
        "description": "Search for activities based on a query or specific criteria",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "user_id": {"type": "string", "description": "Optional user ID for personalization"},
                "activity_type": {"type": "string", "description": "Optional activity type filter"},
                "max_results": {"type": "integer", "description": "Maximum number of results", "default": 5}
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_personalized_mystory_prompt",
        "description": "Get a personalized My Story prompt based on user's interests and background",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "User identifier"}
            },
            "required": ["user_id"]
        }
    },
    # Life Story Recording Tools
    {
        "name": "start_life_story_session",
        "description": "Start a guided life story recording session. This is a multi-turn journey where the user shares memories from different life phases (childhood, education, career, relationships, achievements, challenges). Use this when a user wants to record or share their life story.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "User identifier"}
            },
            "required": ["user_id"]
        }
    },
    {
        "name": "continue_life_story_session",
        "description": "Continue an active life story recording session by saving the user's response and moving to the next phase",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "User identifier"},
                "session_id": {"type": "string", "description": "Session identifier from start_life_story_session"},
                "response_text": {"type": "string", "description": "User's response to the current prompt"},
                "skip_phase": {"type": "boolean", "description": "Skip this phase without recording", "default": False},
                "approximate_date": {"type": "string", "description": "Optional date context like '1960s', 'childhood', 'age 25'"}
            },
            "required": ["user_id", "session_id", "response_text"]
        }
    },
    {
        "name": "get_life_story_sessions",
        "description": "Get all life story sessions for a user, including completed and in-progress sessions",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "User identifier"},
                "include_chunks": {"type": "boolean", "description": "Whether to include detailed memory chunks", "default": False}
            },
            "required": ["user_id"]
        }
    },
    {
        "name": "delete_life_story_session",
        "description": "Delete a life story session and all its recorded memories",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "User identifier"},
                "session_id": {"type": "string", "description": "Session to delete"}
            },
            "required": ["user_id", "session_id"]
        }
    },
    {
        "name": "get_life_story_prompt_for_phase",
        "description": "Get the prompt for a specific life story phase, optionally personalized for a user",
        "parameters": {
            "type": "object",
            "properties": {
                "phase": {"type": "string", "description": "Phase name", "enum": ["introduction", "childhood", "education", "work_career", "relationships", "achievements", "challenges", "special_memories", "summary"]},
                "user_id": {"type": "string", "description": "Optional user ID for personalization"}
            },
            "required": ["phase"]
        }
    }
]
