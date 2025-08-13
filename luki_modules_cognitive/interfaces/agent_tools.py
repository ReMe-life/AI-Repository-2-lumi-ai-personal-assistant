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
from ..config import get_config


class CognitiveTools:
    """Tools for LUKi agent to access cognitive module functionality"""
    
    def __init__(self):
        self.config = get_config()
        self.recommender = ActivityRecommender()
        self.catalog = ActivityCatalog()
        self.elr_adapter = ELRAdapter()
    
    async def close(self):
        """Close resources"""
        await self.recommender.close()
    
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
    }
]
