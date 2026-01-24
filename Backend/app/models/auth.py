"""
Authentication Schemas
======================
Pydantic models for authentication requests and responses.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class LoginRequest(BaseModel):
    """Request schema for user login."""
    username: str = Field(..., description="Email or phone number")
    password: str = Field(..., min_length=8)
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "parent@example.com",
                "password": "SecurePassword123"
            }
        }


class LoginResponse(BaseModel):
    """Response schema for successful login."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_at: datetime = Field(..., description="Access token expiration time (ISO format)")
    user_id: str
    email: str
    full_name: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_at": "2024-01-15T10:30:00Z",
                "user_id": "507f1f77bcf86cd799439011",
                "email": "parent@example.com",
                "full_name": "Ramesh Kumar"
            }
        }


class RegisterRequest(BaseModel):
    """Request schema for user registration."""
    email: EmailStr
    phone_number: str = Field(..., pattern=r'^\+91[6-9]\d{9}$')
    full_name: str = Field(..., min_length=2, max_length=100)
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


class RegisterResponse(BaseModel):
    """Response schema for successful registration."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_at: datetime = Field(..., description="Access token expiration time (ISO format)")
    user_id: str
    message: str = "User registered successfully"
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_at": "2024-01-15T10:30:00Z",
                "user_id": "507f1f77bcf86cd799439011",
                "message": "User registered successfully"
            }
        }


class ErrorResponse(BaseModel):
    """Generic error response schema."""
    detail: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Invalid credentials"
            }
        }


class RefreshRequest(BaseModel):
    """Request schema for token refresh."""
    refresh_token: str = Field(..., description="Valid refresh token")
    
    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


class RefreshResponse(BaseModel):
    """Response schema for successful token refresh."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_at: datetime = Field(..., description="Access token expiration time (ISO format)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_at": "2024-01-15T10:30:00Z"
            }
        }
