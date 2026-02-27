"""
Profile Model - Student Profiles
=================================
Pydantic models for the student profiles collection.
Represents individual learner profiles under a master account (Netflix-style).
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime


class PyObjectId(str):
    """Custom ID type for Pydantic v2 models (DynamoDB compatible)."""
    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type, _handler):
        from pydantic_core import core_schema
        
        def validate(value, _info=None):
            if isinstance(value, str) and len(value) > 0:
                return value
            raise ValueError("Invalid ID - must be a non-empty string")
        
        return core_schema.with_info_plain_validator_function(
            validate,
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda x: str(x)
            )
        )


class Gamification(BaseModel):
    """Gamification stats for student profile."""
    xp: int = Field(default=0, ge=0)
    current_streak_days: int = Field(default=0, ge=0)
    last_activity_date: Optional[datetime] = None
    badges: List[str] = Field(default_factory=list)

class SubjectInsightData(BaseModel):
    """Legacy subject insight data format (for backwards compatibility)."""
    subject: str
    average_score: Optional[float] = 0.0
    total_quizzes: Optional[int] = 0
    performance_trend: Optional[str] = "stable"
    weak_topics: Optional[List[str]] = Field(default_factory=list)
    strong_topics: Optional[List[str]] = Field(default_factory=list)
    recommendation: Optional[str] = ""

class WeeklyGoal(BaseModel):
    """Weekly goal with bilingual support."""
    goal: str
    goal_hindi: Optional[str] = ""
    subject: Optional[str] = "General"

class OverallAssessment(BaseModel):
    """Overall assessment from insights."""
    level: str = "average"
    summary: str = ""
    summary_hindi: Optional[str] = ""

class StrengthItem(BaseModel):
    """Strength item with praise."""
    area: str
    praise: str = ""
    praise_hindi: Optional[str] = ""

class WeakTopicExplanation(BaseModel):
    """Weak topic explanation."""
    topic: str
    explanation: str = ""
    explanation_hindi: Optional[str] = ""

class SubjectInsight(BaseModel):
    """Subject insight from quiz analysis."""
    subject: str
    status: Optional[str] = "average"
    score_average: Optional[float] = 0.0
    performance_trend: Optional[str] = "stable"
    improvement_areas: Optional[List[str]] = Field(default_factory=list)
    strong_areas: Optional[List[str]] = Field(default_factory=list)
    recommendation: Optional[str] = ""
    recommendation_hindi: Optional[str] = ""

class StoredLearningInsights(BaseModel):
    """
    Learning insights stored in profile after quiz completion.
    Supports both the new LLM format and legacy flat format.
    Uses Union types to accept both string and dict formats for array fields.
    """
    # Metadata
    generated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    analysis_period_days: Optional[int] = 30
    has_data: Optional[bool] = True
    rag_enhanced: Optional[bool] = False
    
    # Core stats
    total_quizzes: Optional[int] = 0
    overall_average: Optional[float] = 0.0
    performance_trend: Optional[str] = "neutral"
    
    # New LLM format fields - using Any to accept both old and new formats
    overall_assessment: Optional[OverallAssessment] = None
    subject_insights: Optional[List[SubjectInsight]] = Field(default_factory=list)
    
    # These fields accept BOTH strings (old format) and dicts (new format)
    weak_topics_explanation: Optional[List] = Field(default_factory=list)  # List[str | WeakTopicExplanation]
    strengths: Optional[List] = Field(default_factory=list)  # List[str | StrengthItem]
    weekly_goals: Optional[List] = Field(default_factory=list)  # List[str | WeeklyGoal]
    
    personalized_recommendations: Optional[List[str]] = Field(default_factory=list)
    motivational_message: Optional[str] = ""
    motivational_message_hindi: Optional[str] = ""
    
    # Profile info (may be included)
    profile_name: Optional[str] = None
    grade_level: Optional[str] = None
    
    # Legacy fields for backwards compatibility
    overall_score: Optional[float] = None
    total_quizzes_analyzed: Optional[int] = None
    subjects: Optional[List[SubjectInsightData]] = None
    weak_areas_summary: Optional[str] = None
    strengths_summary: Optional[str] = None

    class Config:
        extra = "allow"  # Allow extra fields for flexibility
        json_schema_extra = {
            "example": {
                "generated_at": "2024-01-20T10:30:00",
                "total_quizzes": 5,
                "overall_average": 75.5,
                "overall_assessment": {
                    "level": "good",
                    "summary": "You're doing well!",
                    "summary_hindi": "आप अच्छा कर रहे हैं!"
                },
                "weekly_goals": [
                    {"goal": "Practice daily", "goal_hindi": "रोज अभ्यास करें", "subject": "Math"}
                ]
            }
        }


class LearningPreferences(BaseModel):
    """Learning preferences for the student."""
    voice_enabled: bool = True  # Default to TTS enabled
    
    class Config:
        json_schema_extra = {
            "example": {
                "voice_enabled": True
            }
        }


class ProfileBase(BaseModel):
    """Base profile fields shared across operations."""
    name: str = Field(..., min_length=2, max_length=50)
    age: int = Field(..., ge=5, le=18)  # Age range for students
    grade_level: str = Field(..., pattern=r'^([1-9]|1[0-2])(th|st|nd|rd)$')  # 1st to 12th
    preferred_language: str = Field(default="Hindi")
    
    @field_validator('preferred_language')
    @classmethod
    def validate_language(cls, v: str) -> str:
        """Validate supported languages."""
        supported = {
            "Hindi", "English", "Bengali", "Tamil", "Telugu", 
            "Marathi", "Gujarati", "Kannada", "Malayalam", 
            "Punjabi", "Odia", "Assamese", "Urdu"
        }
        if v not in supported:
            raise ValueError(f'Language must be one of: {", ".join(supported)}')
        return v
    
    @field_validator('grade_level')
    @classmethod
    def validate_grade(cls, v: str) -> str:
        """Normalize grade level format."""
        # Extract number and add appropriate suffix
        import re
        match = re.match(r'^(\d+)', v)
        if match:
            num = int(match.group(1))
            if 1 <= num <= 12:
                # Add proper suffix
                if num == 1:
                    return "1st"
                elif num == 2:
                    return "2nd"
                elif num == 3:
                    return "3rd"
                else:
                    return f"{num}th"
        raise ValueError('Grade level must be between 1st and 12th')


class ProfileCreate(ProfileBase):
    """Schema for creating a new student profile."""
    avatar: Optional[str] = Field(default="default_avatar.png")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Aarav",
                "age": 12,
                "grade_level": "6th",
                "preferred_language": "Hindi",
                "avatar": "avatar_boy_1.png"
            }
        }


class ProfileUpdate(BaseModel):
    """Schema for updating profile information."""
    name: Optional[str] = None
    age: Optional[int] = Field(default=None, ge=5, le=18)
    grade_level: Optional[str] = None
    preferred_language: Optional[str] = None
    avatar: Optional[str] = None
    learning_preferences: Optional[LearningPreferences] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Aarav Kumar",
                "avatar": "avatar_boy_2.png",
                "learning_preferences": {
                    "voice_enabled": False
                }
            }
        }


class ProfileInDB(ProfileBase):
    """Profile model as stored in MongoDB."""
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    master_user_id: PyObjectId
    avatar: str = Field(default="default_avatar.png")
    gamification: Gamification = Field(default_factory=Gamification)
    learning_preferences: LearningPreferences = Field(default_factory=LearningPreferences)
    learning_insights: Optional[StoredLearningInsights] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
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
                    "badges": ["math_wizard", "early_bird"]
                },
                "learning_preferences": {
                    "voice_enabled": True
                },
                "created_at": "2024-01-15T10:30:00",
                "updated_at": "2024-01-20T15:45:00"
            }
        }


class ProfileResponse(BaseModel):
    """Profile response model."""
    id: str = Field(..., alias="_id")
    master_user_id: str
    name: str
    age: int
    grade_level: str
    preferred_language: str
    avatar: str
    gamification: Gamification
    learning_preferences: LearningPreferences
    learning_insights: Optional[StoredLearningInsights] = None
    created_at: datetime
    updated_at: datetime
    
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
                    "badges": ["math_wizard", "early_bird"]
                },
                "learning_preferences": {
                    "voice_enabled": True
                },
                "created_at": "2024-01-15T10:30:00",
                "updated_at": "2024-01-20T15:45:00"
            }
        }


class ProfileWithStats(ProfileResponse):
    """Extended profile response with additional statistics."""
    total_conversations: int = 0
    total_quizzes_completed: int = 0
    average_quiz_score: float = 0.0
    
    class Config:
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
                    "badges": ["math_wizard", "early_bird"]
                },
                "learning_preferences": {
                    "voice_enabled": True
                },
                "created_at": "2024-01-15T10:30:00",
                "updated_at": "2024-01-20T15:45:00",
                "total_conversations": 25,
                "total_quizzes_completed": 10,
                "average_quiz_score": 85.5
            }
        }
