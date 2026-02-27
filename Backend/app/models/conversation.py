"""
Conversation Model - Chat Sessions
===================================
Pydantic models for the conversations collection.
Represents chat sessions between students and the AI tutor.
"""

from pydantic import BaseModel, Field
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


class ConversationCreate(BaseModel):
    """Schema for creating a new conversation."""
    profile_id: str = Field(..., description="Student profile ID")
    topic: Optional[str] = Field(default=None, description="Optional conversation topic")
    
    class Config:
        json_schema_extra = {
            "example": {
                "profile_id": "507f1f77bcf86cd799439012",
                "topic": "Photosynthesis"
            }
        }


class ConversationInDB(BaseModel):
    """Conversation model as stored in MongoDB."""
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    profile_id: PyObjectId
    title: str = Field(default="New Conversation")
    subject_tag: Optional[str] = Field(default=None)
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
                "_id": "507f1f77bcf86cd799439013",
                "profile_id": "507f1f77bcf86cd799439012",
                "title": "Photosynthesis Explanation",
                "subject_tag": "Biology",
                "created_at": "2024-01-20T10:30:00",
                "updated_at": "2024-01-20T15:45:00"
            }
        }


class ConversationResponse(BaseModel):
    """Conversation response model."""
    id: str = Field(..., alias="_id")
    profile_id: str
    title: str
    subject_tag: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    message_count: int = 0  # Added for list view
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "_id": "507f1f77bcf86cd799439013",
                "profile_id": "507f1f77bcf86cd799439012",
                "title": "Photosynthesis Explanation",
                "subject_tag": "Biology",
                "created_at": "2024-01-20T10:30:00",
                "updated_at": "2024-01-20T15:45:00",
                "message_count": 15
            }
        }


class ConversationUpdate(BaseModel):
    """Schema for updating conversation metadata."""
    title: Optional[str] = None
    subject_tag: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Understanding Photosynthesis",
                "subject_tag": "Biology"
            }
        }
