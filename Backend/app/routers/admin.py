"""
Admin Router - Knowledge Base Management
=========================================
Admin endpoints for managing the RAG knowledge base.

DigiMasterJi - Multilingual AI Tutor for Rural Education
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, status
from typing import List, Optional
import logging
from app.models.knowledge_base import (
    SubjectEnum,
    LanguageEnum,
    DocumentUploadResponse,
    VectorSearchRequest,
    VectorSearchResult
)
from app.database import knowledge_base as kb_db
from app.services.rag_service import rag_service
from app.utils.security import get_current_user

# Configure logging for admin operations
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    summary="Upload PDF for RAG ingestion",
    description="Upload a PDF document to S3 for Bedrock Knowledge Base ingestion."
)
async def upload_document(
    file: UploadFile = File(..., description="PDF file to upload"),
    subject: SubjectEnum = Form(..., description="Subject category"),
    language: LanguageEnum = Form(default=LanguageEnum.ENGLISH, description="Document language"),
    tags: Optional[str] = Form(default="", description="Comma-separated tags"),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload a PDF document to S3 for RAG ingestion via Bedrock Knowledge Bases.
    
    This endpoint:
    1. Validates the uploaded file is a PDF
    2. Uploads the PDF to S3
    3. Tracks the upload in DynamoDB
    4. Optionally triggers Bedrock Knowledge Base sync
    
    Requires JWT authentication.
    """
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported"
        )
    
    # Read file content
    try:
        pdf_bytes = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error reading file: {str(e)}"
        )
    
    if len(pdf_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file uploaded"
        )
    
    try:
        logger.info(f"[RAG UPLOAD] Uploading PDF to S3: {file.filename} (subject: {subject.value}, language: {language.value})")
        
        # Upload PDF to S3 and track in DynamoDB
        upload_result = await kb_db.upload_document_to_s3(
            file_content=pdf_bytes,
            filename=file.filename,
            subject=subject.value,
            language=language.value,
            content_type="application/pdf"
        )
        
        logger.info(f"[RAG UPLOAD] Successfully uploaded document {upload_result['documentId']} to S3")
        
        # Trigger Bedrock Knowledge Base sync
        try:
            sync_result = await kb_db.trigger_knowledge_base_sync()
            logger.info(f"[RAG UPLOAD] Knowledge Base sync: {sync_result.get('status')}")
        except Exception as sync_error:
            logger.warning(f"[RAG UPLOAD] KB sync warning (non-fatal): {sync_error}")
        
        return DocumentUploadResponse(
            success=True,
            message=f"Successfully uploaded document to S3. Bedrock will process and index automatically.",
            filename=file.filename,
            chunks_processed=1,  # S3 upload is single document
            subject=subject.value,
            language=language.value
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading document: {str(e)}"
        )


@router.post(
    "/search",
    response_model=List[VectorSearchResult],
    summary="Vector search in knowledge base",
    description="Perform semantic search in the knowledge base using Bedrock Knowledge Bases."
)
async def search_knowledge_base(
    request: VectorSearchRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Search the knowledge base using Bedrock Knowledge Bases.
    
    This endpoint:
    1. Sends the query to Bedrock Knowledge Bases
    2. Bedrock handles embedding and vector search internally
    3. Returns the most relevant chunks with similarity scores
    """
    try:
        # Perform vector search using Bedrock Knowledge Bases
        # Note: The new vector_search takes query_text directly
        results = await kb_db.vector_search(
            query_text=request.query,
            limit=request.limit,
            subject=request.subject.value if request.subject else None,
            language=request.language.value if request.language else None
        )
        
        # Convert to response format
        return [
            VectorSearchResult(
                id=r["_id"],
                title=r.get("title", "Knowledge Base Result"),
                content_chunk=r["content_chunk"],
                subject=r["subject"],
                language=r["language"],
                score=r["score"],
                tags=r.get("tags", [])
            )
            for r in results
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search error: {str(e)}"
        )


@router.get(
    "/documents",
    summary="List all uploaded documents",
    description="Get a summary of all uploaded source files in the knowledge base."
)
async def list_documents(
    current_user: dict = Depends(get_current_user)
):
    """List all uploaded documents with their chunk counts."""
    from app.database.mongodb_embeddings import get_documents_list
    
    try:
        # Get documents from DynamoDB (metadata)
        dynamo_docs = await kb_db.get_all_source_files()
        
        # Get documents from MongoDB (actual embeddings with chunk counts)
        mongo_docs = await get_documents_list()
        
        # Create a map of MongoDB docs by filename for quick lookup
        mongo_map = {}
        for doc in mongo_docs:
            filename = doc.get("filename", "")
            if filename:
                mongo_map[filename] = doc
        
        # Merge the documents - add chunk_count from MongoDB
        merged_docs = []
        for doc in dynamo_docs:
            filename = doc.get("filename", "")
            mongo_doc = mongo_map.get(filename, {})
            
            merged_docs.append({
                **doc,
                "chunk_count": mongo_doc.get("chunk_count", 0),
                "source_uri": mongo_doc.get("source_uri", "")
            })
        
        # Also include MongoDB-only docs (in case DynamoDB is out of sync)
        dynamo_filenames = {d.get("filename", "") for d in dynamo_docs}
        for mongo_doc in mongo_docs:
            filename = mongo_doc.get("filename", "")
            if filename and filename not in dynamo_filenames:
                merged_docs.append({
                    "filename": filename,
                    "subject": mongo_doc.get("subject", "unknown"),
                    "language": mongo_doc.get("language", "unknown"),
                    "chunk_count": mongo_doc.get("chunk_count", 0),
                    "source_uri": mongo_doc.get("source_uri", ""),
                    "status": "synced"  # Exists in KB but not in DynamoDB metadata
                })
        
        return {
            "success": True,
            "documents": merged_docs,
            "total": len(merged_docs)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching documents: {str(e)}"
        )


@router.get(
    "/stats",
    summary="Knowledge base statistics",
    description="Get statistics about the knowledge base."
)
async def get_stats(
    current_user: dict = Depends(get_current_user)
):
    """Get knowledge base statistics."""
    try:
        stats = await kb_db.get_knowledge_base_stats()
        return {
            "success": True,
            **stats
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching stats: {str(e)}"
        )


@router.delete(
    "/documents/{filename}",
    summary="Delete document by filename",
    description="Delete all chunks from a specific source file."
)
async def delete_document(
    filename: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete all chunks from a specific source file."""
    try:
        deleted_count = await kb_db.delete_chunks_by_source_file(filename)
        
        if deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No document found with filename: {filename}"
            )
        
        return {
            "success": True,
            "message": f"Deleted {deleted_count} chunks",
            "filename": filename,
            "chunks_deleted": deleted_count
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting document: {str(e)}"
        )


@router.get(
    "/rag-info",
    summary="RAG service information",
    description="Get information about the RAG service configuration."
)
async def get_rag_info(
    current_user: dict = Depends(get_current_user)
):
    """Get RAG service configuration info."""
    return {
        "success": True,
        **rag_service.get_info()
    }


@router.post(
    "/sync",
    summary="Trigger Knowledge Base sync",
    description="Manually trigger Bedrock Knowledge Base to process new documents from S3."
)
async def trigger_sync(
    current_user: dict = Depends(get_current_user)
):
    """
    Manually trigger Bedrock Knowledge Base sync/ingestion.
    
    Use this to:
    1. Force a sync after uploading documents
    2. Check if sync is working correctly
    
    Returns the job ID which can be used to check status.
    """
    try:
        result = await kb_db.trigger_knowledge_base_sync()
        return {
            "success": True,
            **result
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger sync: {str(e)}"
        )


@router.get(
    "/sync/jobs",
    summary="List ingestion jobs",
    description="List recent Knowledge Base ingestion jobs with their status."
)
async def list_sync_jobs(
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """
    List recent ingestion jobs for the Knowledge Base.
    
    Returns job statuses:
    - STARTING: Job is being initialized
    - IN_PROGRESS: Job is processing documents
    - COMPLETE: Job finished successfully
    - FAILED: Job failed (check failureReasons)
    
    Documents are indexed and searchable once status is COMPLETE.
    """
    try:
        result = await kb_db.list_ingestion_jobs(limit=limit)
        return {
            "success": True,
            **result
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list ingestion jobs: {str(e)}"
        )


@router.get(
    "/sync/jobs/{job_id}",
    summary="Get ingestion job status",
    description="Get detailed status of a specific ingestion job."
)
async def get_sync_job_status(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get detailed status of a specific ingestion job.
    
    Includes:
    - Current status (STARTING, IN_PROGRESS, COMPLETE, FAILED)
    - Statistics (documents scanned, indexed, failed)
    - Timestamps (started, updated)
    - Failure reasons if applicable
    """
    try:
        result = await kb_db.get_ingestion_job_status(job_id)
        return {
            "success": True,
            **result
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job status: {str(e)}"
        )
