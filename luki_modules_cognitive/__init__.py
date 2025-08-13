"""
LUKi Cognitive Modules Package

Personalised activity creation, cognitive stimulation & wellbeing analytics for ReMeLife
"""

__version__ = "0.1.0"
__author__ = "ReMeLife Team"
__email__ = "dev@remelife.com"

from .recommender.recommend import ActivityRecommender
from .data.activity_catalog import ActivityCatalog
from .interfaces.agent_tools import CognitiveTools

__all__ = [
    "ActivityRecommender",
    "ActivityCatalog", 
    "CognitiveTools"
]
