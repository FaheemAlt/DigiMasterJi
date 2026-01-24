"""
Sync Models - Data Synchronization
===================================
Pydantic models for the sync/pull endpoint.
Used to fetch all user data (profiles, conversations, messages) on login.

Note: Audio data is excluded from sync responses as per requirement.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class SyncMessageResponse(BaseModel):
    """
    Message model for sync response.
    Excludes audio fields (audio_url, audio_base64, etc.) as audio is not synced.
    """
    id: str = Field(..., alias="_id")
    conversation_id: str
    profile_id: str
    role: str  # "user" or "assistant"
    content: str
    content_translated: Optional[str] = None
    timestamp: datetime
    rag_references: List[str] = Field(default_factory=list)
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "_id": "507f1f77bcf86cd799439014",
                "conversation_id": "507f1f77bcf86cd799439013",
                "profile_id": "507f1f77bcf86cd799439012",
                "role": "user",
                "content": "Photosynthesis kya hai?",
                "content_translated": "What is photosynthesis?",
                "timestamp": "2024-01-20T10:30:00",
                "rag_references": []
            }
        }


class SyncConversationResponse(BaseModel):
    """
    Conversation model for sync response.
    Includes nested messages from the past 15 days.
    """
    id: str = Field(..., alias="_id")
    profile_id: str
    title: str
    subject_tag: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    messages: List[SyncMessageResponse] = Field(default_factory=list)
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "_id": "507f1f77bcf86cd799439013",
                "profile_id": "507f1f77bcf86cd799439012",
                "title": "Photosynthesis Discussion",
                "subject_tag": "Biology",
                "created_at": "2024-01-20T10:00:00",
                "updated_at": "2024-01-20T15:30:00",
                "messages": []
            }
        }


class SyncGamificationResponse(BaseModel):
    """Gamification stats for sync response."""
    xp: int = 0
    current_streak_days: int = 0
    last_activity_date: Optional[datetime] = None
    badges: List[str] = Field(default_factory=list)


class SyncLearningPreferencesResponse(BaseModel):
    """Learning preferences for sync response."""
    voice_enabled: bool = True


class SyncProfileResponse(BaseModel):
    """
    Profile model for sync response.
    Includes nested conversations with their messages.
    """
    id: str = Field(..., alias="_id")
    master_user_id: str
    name: str
    age: int
    grade_level: str
    preferred_language: str
    avatar: str
    gamification: SyncGamificationResponse
    learning_preferences: SyncLearningPreferencesResponse
    created_at: datetime
    updated_at: datetime
    conversations: List[SyncConversationResponse] = Field(default_factory=list)
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "_id": "507f1f77bcf86cd799439012",
                "master_user_id": "507f1f77bcf86cd799439011",
                "name": "Aarav",
                "age": 12,
                "grade_level": "6th",
                "preferred_language": "Hindi",
                "avatar": "avatar_boy_1.png",
                "gamification": {
                    "xp": 1500,
                    "current_streak_days": 3,
                    "last_activity_date": "2024-01-20T10:30:00",
                    "badges": ["math_wizard"]
                },
                "learning_preferences": {
                    "voice_enabled": True
                },
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-20T15:30:00",
                "conversations": []
            }
        }


class SyncPullResponse(BaseModel):
    """
    Complete sync response for /sync/pull endpoint.
    
    Returns all user data in a nested structure:
    - User info (master account)
    - Profiles (all student profiles under this account)
      - Conversations (all conversations for each profile)
        - Messages (past 15 days only, no audio)
    """
    success: bool = True
    sync_timestamp: datetime = Field(default_factory=datetime.utcnow)
    message: str = "Data synced successfully"
    
    # User info
    user_id: str
    user_email: str
    user_full_name: str
    
    # Nested data
    profiles: List[SyncProfileResponse] = Field(default_factory=list)
    
    # Metadata
    total_profiles: int = 0
    total_conversations: int = 0
    total_messages: int = 0
    sync_period_days: int = 15
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "sync_timestamp": "2024-01-20T16:00:00",
                "message": "Data synced successfully",
                "user_id": "507f1f77bcf86cd799439011",
                "user_email": "parent@example.com",
                "user_full_name": "Ramesh Kumar",
                "profiles": [],
                "total_profiles": 2,
                "total_conversations": 5,
                "total_messages": 150,
                "sync_period_days": 15
            }
        }
