"""
Knowledge Base Database Operations - AWS Version
=================================================
S3 for document storage, DynamoDB for metadata tracking,
and Bedrock Knowledge Bases for vector search.

DigiMasterJi - Multilingual AI Tutor for Rural Education
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import os
import uuid
import boto3
from botocore.exceptions import ClientError
from app.database.dynamo import (
    get_table,
    generate_id,
    datetime_to_iso,
    iso_to_datetime,
    serialize_for_dynamo,
    deserialize_from_dynamo,
    TABLE_KNOWLEDGE_BASE
)

# Configure logging
logger = logging.getLogger(__name__)

# Resource names from environment (TABLE_KNOWLEDGE_BASE imported from dynamo.py)
S3_BUCKET = os.getenv("S3_KNOWLEDGE_BUCKET", "digimasterji-knowledge")
BEDROCK_KB_ID = os.getenv("BEDROCK_KNOWLEDGE_BASE_ID", "")
BEDROCK_DATA_SOURCE_ID = os.getenv("BEDROCK_DATA_SOURCE_ID", "")


def get_s3_client():
    """Get S3 client."""
    return boto3.client(
        "s3",
        region_name=os.getenv("AWS_REGION", "us-east-1")
    )


def get_bedrock_agent_client():
    """Get Bedrock Agent client for Knowledge Bases."""
    return boto3.client(
        "bedrock-agent",
        region_name=os.getenv("AWS_REGION", "us-east-1")
    )


def get_bedrock_agent_runtime_client():
    """Get Bedrock Agent Runtime client for querying Knowledge Bases."""
    return boto3.client(
        "bedrock-agent-runtime",
        region_name=os.getenv("AWS_REGION", "us-east-1")
    )


def get_knowledge_base_table():
    """Get the DynamoDB knowledge_base table."""
    return get_table(TABLE_KNOWLEDGE_BASE)


async def upload_document_to_s3(
    file_content: bytes,
    filename: str,
    subject: str,
    language: str,
    content_type: str = "application/pdf"
) -> Dict[str, Any]:
    """
    Upload a document to S3 and track it in DynamoDB.
    
    Args:
        file_content: Raw file bytes
        filename: Original filename
        subject: Subject category (math, science, etc.)
        language: Language code (en, hi, te, etc.)
        content_type: MIME type of the file
        
    Returns:
        Document metadata including S3 key and document ID
    """
    s3_client = get_s3_client()
    table = get_knowledge_base_table()
    
    # Generate unique S3 key
    doc_id = generate_id()
    s3_key = f"{subject}/{language}/{doc_id}_{filename}"
    
    try:
        # Upload to S3
        logger.info(f"[KB UPLOAD] Uploading {filename} to S3 bucket {S3_BUCKET}...")
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=file_content,
            ContentType=content_type,
            Metadata={
                "subject": subject,
                "language": language,
                "original_filename": filename
            }
        )
        
        # Track in DynamoDB
        now = datetime.utcnow()
        doc_record = {
            "documentId": doc_id,
            "filename": filename,
            "s3Key": s3_key,
            "s3Bucket": S3_BUCKET,
            "subject": subject,
            "language": language,
            "contentType": content_type,
            "uploadedAt": datetime_to_iso(now),
            "status": "uploaded",  # uploaded -> ingesting -> ready -> error
            "fileSize": len(file_content)
        }
        
        table.put_item(Item=serialize_for_dynamo(doc_record))
        
        logger.info(f"[KB UPLOAD] Successfully uploaded document {doc_id}: {filename}")
        
        return {
            "documentId": doc_id,
            "s3Key": s3_key,
            "filename": filename,
            "subject": subject,
            "language": language
        }
        
    except ClientError as e:
        logger.error(f"[KB UPLOAD] Failed to upload {filename}: {e}")
        raise


async def trigger_knowledge_base_sync() -> Dict[str, Any]:
    """
    Trigger Bedrock Knowledge Base to sync/ingest new documents from S3.
    
    Returns:
        Ingestion job details
    """
    if not BEDROCK_KB_ID or not BEDROCK_DATA_SOURCE_ID:
        logger.warning("[KB SYNC] Bedrock Knowledge Base ID or Data Source ID not configured")
        return {"status": "skipped", "message": "Knowledge Base not configured"}
    
    bedrock_agent = get_bedrock_agent_client()
    
    try:
        logger.info(f"[KB SYNC] Starting ingestion job for Knowledge Base {BEDROCK_KB_ID}...")
        
        response = bedrock_agent.start_ingestion_job(
            knowledgeBaseId=BEDROCK_KB_ID,
            dataSourceId=BEDROCK_DATA_SOURCE_ID
        )
        
        job_id = response.get("ingestionJob", {}).get("ingestionJobId", "")
        logger.info(f"[KB SYNC] Ingestion job started: {job_id}")
        
        return {
            "status": "started",
            "jobId": job_id,
            "knowledgeBaseId": BEDROCK_KB_ID
        }
        
    except ClientError as e:
        logger.error(f"[KB SYNC] Failed to start ingestion: {e}")
        raise


async def get_ingestion_job_status(job_id: str) -> Dict[str, Any]:
    """
    Get the status of an ingestion job.
    
    Args:
        job_id: The ingestion job ID
        
    Returns:
        Job status details including status, statistics, and timestamps
    """
    if not BEDROCK_KB_ID or not BEDROCK_DATA_SOURCE_ID:
        return {"status": "error", "message": "Knowledge Base not configured"}
    
    bedrock_agent = get_bedrock_agent_client()
    
    try:
        response = bedrock_agent.get_ingestion_job(
            knowledgeBaseId=BEDROCK_KB_ID,
            dataSourceId=BEDROCK_DATA_SOURCE_ID,
            ingestionJobId=job_id
        )
        
        job = response.get("ingestionJob", {})
        
        return {
            "jobId": job.get("ingestionJobId"),
            "status": job.get("status"),  # STARTING, IN_PROGRESS, COMPLETE, FAILED
            "startedAt": job.get("startedAt").isoformat() if job.get("startedAt") else None,
            "updatedAt": job.get("updatedAt").isoformat() if job.get("updatedAt") else None,
            "statistics": {
                "numberOfDocumentsScanned": job.get("statistics", {}).get("numberOfDocumentsScanned", 0),
                "numberOfDocumentsFailed": job.get("statistics", {}).get("numberOfDocumentsFailed", 0),
                "numberOfMetadataDocumentsScanned": job.get("statistics", {}).get("numberOfMetadataDocumentsScanned", 0),
                "numberOfMetadataDocumentsFailed": job.get("statistics", {}).get("numberOfMetadataDocumentsFailed", 0),
                "numberOfNewDocumentsIndexed": job.get("statistics", {}).get("numberOfNewDocumentsIndexed", 0),
                "numberOfModifiedDocumentsIndexed": job.get("statistics", {}).get("numberOfModifiedDocumentsIndexed", 0),
                "numberOfDocumentsDeleted": job.get("statistics", {}).get("numberOfDocumentsDeleted", 0),
            },
            "failureReasons": job.get("failureReasons", [])
        }
        
    except ClientError as e:
        logger.error(f"[KB SYNC] Failed to get job status: {e}")
        return {"status": "error", "message": str(e)}


async def list_ingestion_jobs(limit: int = 10) -> Dict[str, Any]:
    """
    List recent ingestion jobs for the Knowledge Base.
    
    Args:
        limit: Maximum number of jobs to return
        
    Returns:
        List of ingestion jobs with status information
    """
    if not BEDROCK_KB_ID or not BEDROCK_DATA_SOURCE_ID:
        return {
            "jobs": [],
            "knowledgeBaseId": None,
            "dataSourceId": None,
            "message": "Knowledge Base not configured"
        }
    
    bedrock_agent = get_bedrock_agent_client()
    
    try:
        response = bedrock_agent.list_ingestion_jobs(
            knowledgeBaseId=BEDROCK_KB_ID,
            dataSourceId=BEDROCK_DATA_SOURCE_ID,
            maxResults=limit,
            sortBy={"attribute": "STARTED_AT", "order": "DESCENDING"}
        )
        
        jobs = []
        for job in response.get("ingestionJobSummaries", []):
            jobs.append({
                "jobId": job.get("ingestionJobId"),
                "status": job.get("status"),
                "startedAt": job.get("startedAt").isoformat() if job.get("startedAt") else None,
                "updatedAt": job.get("updatedAt").isoformat() if job.get("updatedAt") else None,
                "statistics": {
                    "numberOfDocumentsScanned": job.get("statistics", {}).get("numberOfDocumentsScanned", 0),
                    "numberOfDocumentsFailed": job.get("statistics", {}).get("numberOfDocumentsFailed", 0),
                    "numberOfNewDocumentsIndexed": job.get("statistics", {}).get("numberOfNewDocumentsIndexed", 0),
                }
            })
        
        return {
            "jobs": jobs,
            "knowledgeBaseId": BEDROCK_KB_ID,
            "dataSourceId": BEDROCK_DATA_SOURCE_ID,
            "total": len(jobs)
        }
        
    except ClientError as e:
        logger.error(f"[KB SYNC] Failed to list ingestion jobs: {e}")
        return {
            "jobs": [],
            "knowledgeBaseId": BEDROCK_KB_ID,
            "dataSourceId": BEDROCK_DATA_SOURCE_ID,
            "error": str(e)
        }


async def vector_search(
    query_text: str,
    limit: int = 5,
    subject: Optional[str] = None,
    language: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Perform vector similarity search using Bedrock Knowledge Bases.
    
    Args:
        query_text: The search query text (will be embedded by Bedrock)
        limit: Maximum number of results to return
        subject: Optional filter by subject
        language: Optional filter by language
        
    Returns:
        List of matching documents with relevance scores
    """
    if not BEDROCK_KB_ID:
        logger.warning("[KB SEARCH] Bedrock Knowledge Base ID not configured")
        return []
    
    bedrock_runtime = get_bedrock_agent_runtime_client()
    
    logger.info(f"[KB SEARCH] Querying Knowledge Base (limit={limit}, subject={subject}, language={language})")
    
    try:
        # Build retrieval configuration
        # Use SEMANTIC search (HYBRID requires text search index which may not be configured)
        retrieval_config = {
            "vectorSearchConfiguration": {
                "numberOfResults": limit * 2,  # Get more results for filtering
                "overrideSearchType": "SEMANTIC"  # Use semantic (vector) search
            }
        }
        
        # Add metadata filters if provided
        if subject or language:
            filter_conditions = []
            if subject:
                filter_conditions.append({
                    "equals": {
                        "key": "subject",
                        "value": subject
                    }
                })
            if language:
                filter_conditions.append({
                    "equals": {
                        "key": "language", 
                        "value": language
                    }
                })
            
            if len(filter_conditions) == 1:
                retrieval_config["vectorSearchConfiguration"]["filter"] = filter_conditions[0]
            else:
                retrieval_config["vectorSearchConfiguration"]["filter"] = {
                    "andAll": filter_conditions
                }
        
        # Query the Knowledge Base
        response = bedrock_runtime.retrieve(
            knowledgeBaseId=BEDROCK_KB_ID,
            retrievalQuery={
                "text": query_text
            },
            retrievalConfiguration=retrieval_config
        )
        
        # Process results
        results = []
        for i, result in enumerate(response.get("retrievalResults", [])[:limit]):
            content = result.get("content", {})
            location = result.get("location", {})
            metadata = result.get("metadata", {})
            
            # Get source file URI
            source_uri = location.get("s3Location", {}).get("uri", "")
            
            # Parse subject and language from S3 URI path
            # Format: s3://bucket/subject/language/docid_filename.pdf
            parsed_subject = subject or "unknown"
            parsed_language = language or "unknown"
            parsed_filename = "Knowledge Base Result"
            
            if source_uri:
                try:
                    # Remove s3:// prefix and split by /
                    path_parts = source_uri.replace("s3://", "").split("/")
                    if len(path_parts) >= 4:
                        # path_parts[0] = bucket name
                        # path_parts[1] = subject (e.g., "Chemistry")
                        # path_parts[2] = language (e.g., "en")
                        # path_parts[3] = filename (e.g., "docid_original.pdf")
                        parsed_subject = path_parts[1] if not subject else subject
                        parsed_language = path_parts[2] if not language else language
                        
                        # Extract original filename (remove doc_id prefix)
                        filename = path_parts[-1]
                        if "_" in filename:
                            # Format: docid_originalfilename.pdf
                            parsed_filename = "_".join(filename.split("_")[1:])
                        else:
                            parsed_filename = filename
                except Exception as parse_err:
                    logger.warning(f"[KB SEARCH] Failed to parse source URI: {parse_err}")
            
            doc = {
                "_id": f"bedrock_{i}",  # Bedrock doesn't return chunk IDs
                "content_chunk": content.get("text", ""),
                "score": result.get("score", 0.0),
                "source_file": source_uri,
                "subject": parsed_subject,
                "language": parsed_language,
                "title": parsed_filename,
                "tags": metadata.get("tags", [])
            }
            results.append(doc)
        
        if results:
            logger.info(f"[KB SEARCH] Found {len(results)} matching chunks (top score: {results[0].get('score', 0):.4f})")
        else:
            logger.info("[KB SEARCH] No matching chunks found in knowledge base")
        
        return results
        
    except ClientError as e:
        logger.error(f"[KB SEARCH] Vector search failed: {e}")
        return []


async def get_document_by_id(doc_id: str) -> Optional[Dict[str, Any]]:
    """Get a document record by its ID."""
    table = get_knowledge_base_table()
    
    try:
        response = table.get_item(Key={"documentId": doc_id})
        item = response.get("Item")
        if item:
            return deserialize_from_dynamo(item)
        return None
    except ClientError as e:
        logger.error(f"[KB] Failed to get document {doc_id}: {e}")
        return None


async def get_documents_by_source_file(filename: str) -> List[Dict[str, Any]]:
    """Get all document records matching a filename."""
    table = get_knowledge_base_table()
    
    try:
        # Scan with filter (not ideal for large datasets, but matches original behavior)
        response = table.scan(
            FilterExpression="filename = :fn",
            ExpressionAttributeValues={":fn": filename}
        )
        
        results = []
        for item in response.get("Items", []):
            results.append(deserialize_from_dynamo(item))
        
        return results
    except ClientError as e:
        logger.error(f"[KB] Failed to get documents for file {filename}: {e}")
        return []


async def delete_document(doc_id: str) -> bool:
    """
    Delete a document from S3 and DynamoDB.
    
    Returns:
        True if successful, False otherwise
    """
    table = get_knowledge_base_table()
    s3_client = get_s3_client()
    
    try:
        # Get document record first
        response = table.get_item(Key={"documentId": doc_id})
        item = response.get("Item")
        
        if not item:
            logger.warning(f"[KB DELETE] Document {doc_id} not found")
            return False
        
        doc = deserialize_from_dynamo(item)
        s3_key = doc.get("s3Key")
        
        # Delete from S3
        if s3_key:
            logger.info(f"[KB DELETE] Deleting {s3_key} from S3...")
            s3_client.delete_object(Bucket=S3_BUCKET, Key=s3_key)
        
        # Delete from DynamoDB
        table.delete_item(Key={"documentId": doc_id})
        
        logger.info(f"[KB DELETE] Successfully deleted document {doc_id}")
        return True
        
    except ClientError as e:
        logger.error(f"[KB DELETE] Failed to delete document {doc_id}: {e}")
        return False


async def delete_documents_by_filename(filename: str) -> int:
    """
    Delete all documents matching a filename.
    
    Returns:
        Number of deleted documents
    """
    docs = await get_documents_by_source_file(filename)
    deleted_count = 0
    
    for doc in docs:
        doc_id = doc.get("documentId")
        if doc_id and await delete_document(doc_id):
            deleted_count += 1
    
    return deleted_count


async def get_all_source_files() -> List[Dict[str, Any]]:
    """
    Get a summary of all uploaded source files.
    
    Returns:
        List of documents with filename, subject, language, and upload time
    """
    table = get_knowledge_base_table()
    
    try:
        response = table.scan()
        
        results = []
        for item in response.get("Items", []):
            doc = deserialize_from_dynamo(item)
            results.append({
                "documentId": doc.get("documentId"),
                "filename": doc.get("filename"),
                "subject": doc.get("subject"),
                "language": doc.get("language"),
                "uploadedAt": doc.get("uploadedAt"),
                "status": doc.get("status"),
                "fileSize": doc.get("fileSize")
            })
        
        # Sort by upload time (newest first)
        results.sort(key=lambda x: x.get("uploadedAt", ""), reverse=True)
        
        return results
        
    except ClientError as e:
        logger.error(f"[KB] Failed to list source files: {e}")
        return []


async def get_knowledge_base_stats() -> Dict[str, Any]:
    """Get statistics about the knowledge base including MongoDB embeddings."""
    from app.database.mongodb_embeddings import get_embeddings_stats
    
    table = get_knowledge_base_table()
    
    # Get DynamoDB document metadata stats
    dynamo_stats = {
        "total_documents": 0,
        "total_size_bytes": 0,
        "by_subject": {},
        "by_language": {}
    }
    
    try:
        response = table.scan()
        items = response.get("Items", [])
        
        dynamo_stats["total_documents"] = len(items)
        
        for item in items:
            doc = deserialize_from_dynamo(item)
            
            # Count by subject
            subject = doc.get("subject", "unknown")
            dynamo_stats["by_subject"][subject] = dynamo_stats["by_subject"].get(subject, 0) + 1
            
            # Count by language
            language = doc.get("language", "unknown")
            dynamo_stats["by_language"][language] = dynamo_stats["by_language"].get(language, 0) + 1
            
            # Sum file sizes
            dynamo_stats["total_size_bytes"] += doc.get("fileSize", 0)
        
    except ClientError as e:
        logger.error(f"[KB] Failed to get DynamoDB stats: {e}")
    
    # Get MongoDB embeddings stats (actual chunk counts)
    mongo_stats = await get_embeddings_stats()
    
    # Combine stats - MongoDB has the actual embeddings/chunks
    return {
        "total_documents": dynamo_stats["total_documents"],
        "total_chunks": mongo_stats.get("total_chunks", 0),
        "unique_files": mongo_stats.get("unique_files", 0),
        "total_size_bytes": dynamo_stats["total_size_bytes"],
        "by_subject": mongo_stats.get("by_subject", {}) or dynamo_stats["by_subject"],
        "by_language": mongo_stats.get("by_language", {}) or dynamo_stats["by_language"],
        "knowledge_base_id": BEDROCK_KB_ID or "not_configured",
        "mongodb_connected": mongo_stats.get("mongodb_connected", False)
    }


async def update_document_status(doc_id: str, status: str) -> bool:
    """
    Update the status of a document.
    
    Args:
        doc_id: Document ID
        status: New status (uploaded, ingesting, ready, error)
        
    Returns:
        True if successful
    """
    table = get_knowledge_base_table()
    
    try:
        table.update_item(
            Key={"documentId": doc_id},
            UpdateExpression="SET #status = :status, updatedAt = :updated",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":status": status,
                ":updated": datetime_to_iso(datetime.utcnow())
            }
        )
        return True
    except ClientError as e:
        logger.error(f"[KB] Failed to update document status: {e}")
        return False


# Legacy compatibility functions (these map to the new API)

async def insert_knowledge_chunk(chunk_data: Dict[str, Any]) -> str:
    """
    Legacy: Insert a single knowledge chunk.
    With Bedrock KB, documents are uploaded whole and chunked by Bedrock.
    This function is kept for API compatibility but logs a warning.
    """
    logger.warning("[KB] insert_knowledge_chunk called but Bedrock handles chunking automatically")
    # Return a fake ID for compatibility
    return generate_id()


async def insert_many_knowledge_chunks(chunks: List[Dict[str, Any]]) -> List[str]:
    """
    Legacy: Insert multiple knowledge chunks.
    With Bedrock KB, documents are uploaded whole and chunked by Bedrock.
    This function is kept for API compatibility but logs a warning.
    """
    logger.warning("[KB] insert_many_knowledge_chunks called but Bedrock handles chunking automatically")
    # Return fake IDs for compatibility
    return [generate_id() for _ in chunks]


async def get_knowledge_chunk_by_id(chunk_id: str) -> Optional[Dict[str, Any]]:
    """
    Legacy: Get a knowledge chunk by ID.
    Maps to get_document_by_id for compatibility.
    """
    return await get_document_by_id(chunk_id)


async def get_chunks_by_source_file(filename: str) -> List[Dict[str, Any]]:
    """
    Legacy: Get chunks by source file.
    Maps to get_documents_by_source_file for compatibility.
    """
    return await get_documents_by_source_file(filename)


async def delete_chunks_by_source_file(filename: str) -> int:
    """
    Legacy: Delete chunks by source file.
    Maps to delete_documents_by_filename for compatibility.
    """
    return await delete_documents_by_filename(filename)
