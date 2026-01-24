"""
User Model - Master Account (Parent/Teacher)
============================================
Pydantic models for the master users collection.
Represents the "Netflix Account Owner" in the profile system.
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
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


class UserSettings(BaseModel):
    """User account settings."""
    sync_enabled: bool = True
    data_saver_mode: bool = True  # For low bandwidth areas

    class Config:
        json_schema_extra = {
            "example": {
                "sync_enabled": True,
                "data_saver_mode": True
            }
        }


class UserBase(BaseModel):
    """Base user fields shared across operations."""
    email: EmailStr
    phone_number: str = Field(..., pattern=r'^\+91[6-9]\d{9}$')  # Indian mobile format
    full_name: str = Field(..., min_length=2, max_length=100)
    
    @field_validator('phone_number')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Validate Indian phone number format."""
        if not v.startswith('+91'):
            raise ValueError('Phone number must start with +91')
        if len(v) != 13:  # +91 + 10 digits
            raise ValueError('Phone number must be 10 digits after +91')
        return v


class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str = Field(..., min_length=8, max_length=100)
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "parent@example.com",
                "phone_number": "+919876543210",
                "full_name": "Ramesh Kumar",
                "password": "SecurePassword123"
            }
        }


class UserUpdate(BaseModel):
    """Schema for updating user information."""
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    full_name: Optional[str] = None
    settings: Optional[UserSettings] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "full_name": "Ramesh Kumar Singh",
                "settings": {
                    "sync_enabled": True,
                    "data_saver_mode": False
                }
            }
        }


class UserInDB(UserBase):
    """User model as stored in MongoDB."""
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    password_hash: str
    registered_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    settings: UserSettings = Field(default_factory=UserSettings)
    refresh_token: Optional[str] = None
    refresh_token_expires: Optional[datetime] = None
    
    class Config:
        populate_by_name = True
        from_attributes = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }
        json_schema_extra = {
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "email": "parent@example.com",
                "phone_number": "+919876543210",
                "full_name": "Ramesh Kumar",
                "password_hash": "$2b$12$...",
                "registered_at": "2024-01-15T10:30:00",
                "last_login": "2024-01-20T15:45:00",
                "settings": {
                    "sync_enabled": True,
                    "data_saver_mode": True
                },
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token_expires": "2024-01-27T15:45:00"
            }
        }


class UserResponse(BaseModel):
    """User response model (without sensitive data)."""
    id: str = Field(..., alias="_id")
    email: EmailStr
    phone_number: str
    full_name: str
    registered_at: datetime
    last_login: Optional[datetime] = None
    settings: UserSettings
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "email": "parent@example.com",
                "phone_number": "+919876543210",
                "full_name": "Ramesh Kumar",
                "registered_at": "2024-01-15T10:30:00",
                "last_login": "2024-01-20T15:45:00",
                "settings": {
                    "sync_enabled": True,
                    "data_saver_mode": True
                }
            }
        }
