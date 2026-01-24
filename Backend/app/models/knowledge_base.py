"""
Knowledge Base Models for RAG
=============================
Pydantic models for the knowledge base collection used in RAG.

DigiMasterJi - Multilingual AI Tutor for Rural Education
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class SubjectEnum(str, Enum):
    """Supported STEM subjects."""
    PHYSICS = "Physics"
    CHEMISTRY = "Chemistry"
    BIOLOGY = "Biology"
    MATHEMATICS = "Mathematics"
    GENERAL_SCIENCE = "General Science"
    ENVIRONMENTAL_SCIENCE = "Environmental Science"


class LanguageEnum(str, Enum):
    """Supported languages."""
    ENGLISH = "en"
    HINDI = "hi"
    BENGALI = "bn"
    TAMIL = "ta"
    TELUGU = "te"
    MARATHI = "mr"
    GUJARATI = "gu"
    KANNADA = "kn"
    MALAYALAM = "ml"
    PUNJABI = "pa"


class KnowledgeBaseCreate(BaseModel):
    """Schema for creating a knowledge base entry (internal use)."""
    title: str = Field(..., description="Title or heading of the content chunk")
    content_chunk: str = Field(..., description="The actual text content for RAG")
    subject: SubjectEnum = Field(..., description="Subject category")
    language: LanguageEnum = Field(default=LanguageEnum.ENGLISH, description="Content language")
    vector_embedding: List[float] = Field(..., description="384-dim vector from MiniLM")
    tags: List[str] = Field(default_factory=list, description="Searchable tags")
    source_file: Optional[str] = Field(None, description="Original PDF filename")
    chunk_index: Optional[int] = Field(None, description="Position of chunk in source document")
    

class KnowledgeBaseDocument(BaseModel):
    """Schema for a knowledge base document from DB."""
    id: str = Field(..., alias="_id")
    title: str
    content_chunk: str
    subject: str
    language: str
    vector_embedding: List[float]
    tags: List[str] = []
    source_file: Optional[str] = None
    chunk_index: Optional[int] = None
    created_at: datetime
    
    class Config:
        populate_by_name = True


class KnowledgeBaseResponse(BaseModel):
    """Schema for API responses (excludes vector embedding)."""
    id: str
    title: str
    content_chunk: str
    subject: str
    language: str
    tags: List[str] = []
    source_file: Optional[str] = None
    created_at: datetime


class DocumentUploadRequest(BaseModel):
    """Request schema for document upload metadata."""
    subject: SubjectEnum = Field(..., description="Subject category for the document")
    language: LanguageEnum = Field(default=LanguageEnum.ENGLISH, description="Document language")
    tags: List[str] = Field(default_factory=list, description="Optional tags for filtering")


class DocumentUploadResponse(BaseModel):
    """Response schema for document upload."""
    success: bool
    message: str
    filename: str
    chunks_processed: int
    subject: str
    language: str


class VectorSearchResult(BaseModel):
    """Schema for vector search results."""
    id: str
    title: str
    content_chunk: str
    subject: str
    language: str
    score: float = Field(..., description="Similarity score (0-1)")
    tags: List[str] = []


class VectorSearchRequest(BaseModel):
    """Request schema for vector search."""
    query: str = Field(..., description="Search query text")
    limit: int = Field(default=5, ge=1, le=20, description="Number of results")
    subject: Optional[SubjectEnum] = Field(None, description="Filter by subject")
    language: Optional[LanguageEnum] = Field(None, description="Filter by language")
