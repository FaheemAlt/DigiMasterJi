"""
MongoDB Atlas Connection for Bedrock KB Embeddings
===================================================
Connects to MongoDB Atlas to query the bedrock_embeddings collection
which is populated by AWS Bedrock Knowledge Base.

DigiMasterJi - Multilingual AI Tutor for Rural Education
"""

import os
import logging
from typing import Dict, Any, List, Optional
from functools import lru_cache

logger = logging.getLogger(__name__)

# MongoDB Atlas connection
_mongo_client = None
_embeddings_collection = None

# Environment variables
MONGODB_URI = os.getenv("MONGODB_URI", "")
MONGODB_DATABASE = os.getenv("MONGODB_KB_DATABASE", "digimasterji_kb")
MONGODB_COLLECTION = os.getenv("MONGODB_KB_COLLECTION", "bedrock_embeddings")


def get_mongo_client():
    """Get or create MongoDB client."""
    global _mongo_client
    
    if _mongo_client is not None:
        return _mongo_client
    
    if not MONGODB_URI:
        logger.warning("[MongoDB] MONGODB_URI not configured - embeddings stats unavailable")
        return None
    
    try:
        from pymongo import MongoClient
        _mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        # Test connection
        _mongo_client.admin.command('ping')
        logger.info("[MongoDB] Connected to MongoDB Atlas for embeddings")
        return _mongo_client
    except Exception as e:
        logger.error(f"[MongoDB] Failed to connect: {e}")
        return None


def get_embeddings_collection():
    """Get the bedrock_embeddings collection."""
    global _embeddings_collection
    
    if _embeddings_collection is not None:
        return _embeddings_collection
    
    client = get_mongo_client()
    if client is None:
        return None
    
    try:
        db = client[MONGODB_DATABASE]
        _embeddings_collection = db[MONGODB_COLLECTION]
        return _embeddings_collection
    except Exception as e:
        logger.error(f"[MongoDB] Failed to get collection: {e}")
        return None


async def get_embeddings_stats() -> Dict[str, Any]:
    """
    Get statistics about embeddings stored in MongoDB Atlas.
    
    Returns:
        Dictionary with total_chunks, unique_files, by_subject, by_language
    """
    collection = get_embeddings_collection()
    
    if collection is None:
        logger.warning("[MongoDB] Collection not available - returning empty stats")
        return {
            "total_chunks": 0,
            "unique_files": 0,
            "by_subject": {},
            "by_language": {},
            "mongodb_connected": False
        }
    
    try:
        # Get total chunk count
        total_chunks = collection.count_documents({})
        
        # Get unique source files
        # The source URI is in metadata.source or x-amz-bedrock-kb-source-uri
        pipeline_files = [
            {
                "$group": {
                    "_id": "$x-amz-bedrock-kb-source-uri"
                }
            },
            {
                "$count": "count"
            }
        ]
        
        files_result = list(collection.aggregate(pipeline_files))
        unique_files = files_result[0]["count"] if files_result else 0
        
        # Get breakdown by subject (extracted from source URI path)
        # URI format: s3://bucket/subject/language/filename
        pipeline_subjects = [
            {
                "$project": {
                    "source_uri": "$x-amz-bedrock-kb-source-uri"
                }
            },
            {
                "$match": {
                    "source_uri": {"$exists": True, "$ne": None}
                }
            }
        ]
        
        # Extract subjects from source URIs
        by_subject = {}
        by_language = {}
        
        sample_docs = list(collection.find({}, {"x-amz-bedrock-kb-source-uri": 1, "metadata": 1}).limit(1000))
        
        for doc in sample_docs:
            source_uri = doc.get("x-amz-bedrock-kb-source-uri", "")
            if source_uri:
                # Parse s3://bucket/subject/language/filename
                parts = source_uri.replace("s3://", "").split("/")
                if len(parts) >= 3:
                    subject = parts[1]  # e.g., "Chemistry"
                    language = parts[2]  # e.g., "en"
                    by_subject[subject] = by_subject.get(subject, 0) + 1
                    by_language[language] = by_language.get(language, 0) + 1
        
        logger.info(f"[MongoDB] Stats: {total_chunks} chunks, {unique_files} files")
        
        return {
            "total_chunks": total_chunks,
            "unique_files": unique_files,
            "by_subject": by_subject,
            "by_language": by_language,
            "mongodb_connected": True
        }
        
    except Exception as e:
        logger.error(f"[MongoDB] Failed to get stats: {e}")
        return {
            "total_chunks": 0,
            "unique_files": 0,
            "by_subject": {},
            "by_language": {},
            "mongodb_connected": False,
            "error": str(e)
        }


async def get_documents_list() -> List[Dict[str, Any]]:
    """
    Get list of documents with chunk counts from MongoDB.
    
    Returns:
        List of documents with filename, subject, language, chunk_count
    """
    collection = get_embeddings_collection()
    
    if collection is None:
        return []
    
    try:
        # Aggregate to get unique documents with chunk counts
        pipeline = [
            {
                "$group": {
                    "_id": "$x-amz-bedrock-kb-source-uri",
                    "chunk_count": {"$sum": 1},
                    "sample_doc": {"$first": "$$ROOT"}
                }
            },
            {
                "$project": {
                    "source_uri": "$_id",
                    "chunk_count": 1,
                    "_id": 0
                }
            }
        ]
        
        results = list(collection.aggregate(pipeline))
        
        documents = []
        for result in results:
            source_uri = result.get("source_uri", "")
            if source_uri:
                # Parse s3://bucket/subject/language/filename
                parts = source_uri.replace("s3://", "").split("/")
                if len(parts) >= 4:
                    filename = parts[-1]  # Last part is filename
                    subject = parts[1]
                    language = parts[2]
                    
                    # Extract original filename (remove doc_id prefix if present)
                    if "_" in filename:
                        # Format: docid_originalfilename.pdf
                        original_filename = "_".join(filename.split("_")[1:])
                    else:
                        original_filename = filename
                    
                    documents.append({
                        "filename": original_filename,
                        "subject": subject,
                        "language": language,
                        "chunk_count": result.get("chunk_count", 0),
                        "source_uri": source_uri
                    })
        
        return documents
        
    except Exception as e:
        logger.error(f"[MongoDB] Failed to get documents list: {e}")
        return []


def close_mongo_connection():
    """Close MongoDB connection."""
    global _mongo_client, _embeddings_collection
    
    if _mongo_client:
        _mongo_client.close()
        _mongo_client = None
        _embeddings_collection = None
        logger.info("[MongoDB] Connection closed")
