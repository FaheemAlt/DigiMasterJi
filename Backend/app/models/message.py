"""
Message Model - Chat Messages
==============================
Pydantic models for the messages collection.
Represents individual messages in conversations between students and AI.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from bson import ObjectId


class PyObjectId(str):
    """Custom ObjectId type for Pydantic v2 models."""
    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type, _handler):
        from pydantic_core import core_schema
        
        def validate(value, _info=None):
            if isinstance(value, ObjectId):
                return str(value)
            if isinstance(value, str):
                if ObjectId.is_valid(value):
                    return value
                raise ValueError("Invalid ObjectId")
            raise ValueError("Invalid ObjectId type")
        
        return core_schema.with_info_plain_validator_function(
            validate,
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda x: str(x)
            )
        )


class MessageCreate(BaseModel):
    """Schema for creating a new message."""
    content: str = Field(..., min_length=1, max_length=5000)
    role: str = Field(default="user", pattern="^(user|assistant)$")
    content_translated: Optional[str] = None
    audio_url: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "Paudhe khana kaise banate hain?",
                "role": "user",
                "content_translated": "How do plants make food?"
            }
        }


class ChatMessageRequest(BaseModel):
    """
    Schema for sending a message in the chat.
    This is what the frontend sends to the /chat/{conversation_id}/message endpoint.
    """
    content: str = Field(..., min_length=1, max_length=5000, description="User's message content")
    include_audio: bool = Field(default=False, description="Whether to include TTS audio in response")
    slow_audio: bool = Field(default=False, description="Whether to speak slowly (useful for learning)")
    stream: bool = Field(default=False, description="Whether to stream the response via SSE")
    low_bandwidth: bool = Field(default=False, description="Low bandwidth mode - uses ASCII diagrams instead of SVG")
    include_diagram: bool = Field(default=True, description="Whether to include visual diagrams when appropriate")
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "Photosynthesis kya hai? Mujhe simple Hindi mein samjhao.",
                "include_audio": True,
                "slow_audio": False,
                "stream": True,
                "low_bandwidth": False,
                "include_diagram": True
            }
        }


class DiagramData(BaseModel):
    """Schema for visual diagram data (SVG or ASCII art)."""
    type: str = Field(..., description="Diagram format: 'svg' or 'ascii'")
    diagram_type: str = Field(..., description="Type of diagram: 'process', 'cycle', 'structure', etc.")
    content: str = Field(..., description="SVG markup or ASCII art content")
    title: str = Field(..., description="Diagram title")
    size_bytes: Optional[int] = Field(None, description="Size in bytes (for SVG)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "svg",
                "diagram_type": "process",
                "content": "<svg>...</svg>",
                "title": "Photosynthesis Process",
                "size_bytes": 4500
            }
        }


class ChatMessageResponse(BaseModel):
    """
    Schema for the AI response from the chat endpoint.
    Returns only the AI's response message, optionally with TTS audio.
    """
    id: str = Field(..., alias="_id", description="Message ID")
    conversation_id: str
    role: str = Field(default="assistant")
    content: str = Field(..., description="AI tutor's response")
    timestamp: datetime
    # Optional TTS audio fields
    audio_base64: Optional[str] = Field(None, description="Base64 encoded MP3 audio of the response")
    audio_format: Optional[str] = Field(None, description="Audio format (e.g., 'mp3')")
    audio_language: Optional[str] = Field(None, description="Language code used for TTS")
    audio_language_name: Optional[str] = Field(None, description="Human-readable language name")
    # Optional diagram for visual learners
    diagram: Optional[DiagramData] = Field(None, description="Visual diagram (SVG or ASCII art) for the explanation")
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "_id": "507f1f77bcf86cd799439014",
                "conversation_id": "507f1f77bcf86cd799439013",
                "role": "assistant",
                "content": "Photosynthesis ek aisa process hai jisme paudhe sunlight ka upyog karke apna khana banate hain...",
                "timestamp": "2024-01-20T10:30:00",
                "audio_base64": "SGVsbG8gV29ybGQ=...",
                "audio_format": "mp3",
                "audio_language": "hi",
                "audio_language_name": "Hindi"
            }
        }


class MessageInDB(BaseModel):
    """Message model as stored in MongoDB."""
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    conversation_id: PyObjectId
    profile_id: PyObjectId
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str
    content_translated: Optional[str] = None
    audio_url: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    rag_references: List[PyObjectId] = Field(default_factory=list)
    # TTS audio fields (stored for assistant messages)
    audio_base64: Optional[str] = None
    audio_format: Optional[str] = None
    audio_language: Optional[str] = None
    audio_language_name: Optional[str] = None
    
    class Config:
        populate_by_name = True
        from_attributes = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }
        json_schema_extra = {
            "example": {
                "_id": "507f1f77bcf86cd799439014",
                "conversation_id": "507f1f77bcf86cd799439013",
                "profile_id": "507f1f77bcf86cd799439012",
                "role": "user",
                "content": "Paudhe khana kaise banate hain?",
                "content_translated": "How do plants make food?",
                "audio_url": None,
                "timestamp": "2024-01-20T10:30:00",
                "rag_references": [],
                "audio_base64": None,
                "audio_format": None,
                "audio_language": None,
                "audio_language_name": None
            }
        }


class MessageResponse(BaseModel):
    """Message response model."""
    id: str = Field(..., alias="_id")
    conversation_id: str
    profile_id: str
    role: str
    content: str
    content_translated: Optional[str] = None
    audio_url: Optional[str] = None
    timestamp: datetime
    rag_references: List[str] = Field(default_factory=list)
    # TTS audio fields (for assistant messages with audio)
    audio_base64: Optional[str] = None
    audio_format: Optional[str] = None
    audio_language: Optional[str] = None
    audio_language_name: Optional[str] = None
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "_id": "507f1f77bcf86cd799439014",
                "conversation_id": "507f1f77bcf86cd799439013",
                "profile_id": "507f1f77bcf86cd799439012",
                "role": "user",
                "content": "Paudhe khana kaise banate hain?",
                "content_translated": "How do plants make food?",
                "audio_url": None,
                "timestamp": "2024-01-20T10:30:00",
                "rag_references": [],
                "audio_base64": None,
                "audio_format": None,
                "audio_language": None,
                "audio_language_name": None
            }
        }


class AudioTranscriptionResponse(BaseModel):
    """
    Response model for the audio transcription (STT) endpoint.
    Returns the transcribed text from the uploaded audio file.
    """
    success: bool = Field(..., description="Whether transcription was successful")
    transcribed_text: str = Field(..., description="The transcribed text from audio")
    language: Optional[str] = Field(None, description="Detected or specified language code")
    language_name: Optional[str] = Field(None, description="Human-readable language name")
    duration_seconds: Optional[float] = Field(None, description="Audio duration in seconds")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "transcribed_text": "Photosynthesis kya hai?",
                "language": "hi",
                "language_name": "Hindi",
                "duration_seconds": 2.5
            }
        }
