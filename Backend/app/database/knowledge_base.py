"""
Knowledge Base Database Operations
===================================
CRUD operations and vector search for the knowledge base collection.

DigiMasterJi - Multilingual AI Tutor for Rural Education
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
import logging
from app.database.mongodb import db

# Configure logging for knowledge base operations
logger = logging.getLogger(__name__)


def get_knowledge_base_collection():
    """Get the knowledge_base collection."""
    return db.client["digimasterji"]["knowledge_base"]


async def insert_knowledge_chunk(chunk_data: Dict[str, Any]) -> str:
    """
    Insert a single knowledge chunk into the database.
    
    Args:
        chunk_data: Dictionary containing chunk data with vector embedding
        
    Returns:
        Inserted document ID as string
    """
    collection = get_knowledge_base_collection()
    chunk_data["created_at"] = datetime.utcnow()
    result = await collection.insert_one(chunk_data)
    return str(result.inserted_id)


async def insert_many_knowledge_chunks(chunks: List[Dict[str, Any]]) -> List[str]:
    """
    Insert multiple knowledge chunks into the database.
    
    Args:
        chunks: List of chunk dictionaries with vector embeddings
        
    Returns:
        List of inserted document IDs
    """
    collection = get_knowledge_base_collection()
    
    # Add timestamps
    for chunk in chunks:
        chunk["created_at"] = datetime.utcnow()
    
    logger.info(f"[KB INSERT] Inserting {len(chunks)} chunks into knowledge_base collection...")
    result = await collection.insert_many(chunks)
    inserted_ids = [str(id) for id in result.inserted_ids]
    logger.info(f"[KB INSERT] Successfully inserted {len(inserted_ids)} documents with IDs: {inserted_ids[:3]}{'...' if len(inserted_ids) > 3 else ''}")
    return inserted_ids


async def vector_search(
    query_embedding: List[float],
    limit: int = 5,
    subject: Optional[str] = None,
    language: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Perform vector similarity search using MongoDB Atlas Vector Search.
    
    Args:
        query_embedding: 384-dimensional vector from the query text
        limit: Maximum number of results to return
        subject: Optional filter by subject
        language: Optional filter by language
        
    Returns:
        List of matching documents with similarity scores
    """
    collection = get_knowledge_base_collection()
    
    logger.info(f"[KB SEARCH] Performing vector search (limit={limit}, subject={subject}, language={language})")
    
    # Build the vector search pipeline
    pipeline = [
        {
            "$vectorSearch": {
                "index": "vector_index",
                "path": "vector_embedding",
                "queryVector": query_embedding,
                "numCandidates": limit * 10,  # Search more candidates for better results
                "limit": limit
            }
        },
        {
            "$project": {
                "_id": 1,
                "title": 1,
                "content_chunk": 1,
                "subject": 1,
                "language": 1,
                "tags": 1,
                "source_file": 1,
                "created_at": 1,
                "score": {"$meta": "vectorSearchScore"}
            }
        }
    ]
    
    # Add filters if provided (post-search filtering)
    match_conditions = {}
    if subject:
        match_conditions["subject"] = subject
    if language:
        match_conditions["language"] = language
    
    if match_conditions:
        pipeline.insert(1, {"$match": match_conditions})
    
    results = []
    async for doc in collection.aggregate(pipeline):
        doc["_id"] = str(doc["_id"])
        results.append(doc)
    
    if results:
        logger.info(f"[KB SEARCH] Found {len(results)} matching chunks (top score: {results[0].get('score', 0):.4f})")
    else:
        logger.info(f"[KB SEARCH] No matching chunks found in knowledge base")
    
    return results


async def get_knowledge_chunk_by_id(chunk_id: str) -> Optional[Dict[str, Any]]:
    """Get a knowledge chunk by its ID."""
    collection = get_knowledge_base_collection()
    doc = await collection.find_one({"_id": ObjectId(chunk_id)})
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc


async def get_chunks_by_source_file(filename: str) -> List[Dict[str, Any]]:
    """Get all chunks from a specific source file."""
    collection = get_knowledge_base_collection()
    results = []
    async for doc in collection.find({"source_file": filename}):
        doc["_id"] = str(doc["_id"])
        results.append(doc)
    return results


async def delete_chunks_by_source_file(filename: str) -> int:
    """
    Delete all chunks from a specific source file.
    
    Returns:
        Number of deleted documents
    """
    collection = get_knowledge_base_collection()
    result = await collection.delete_many({"source_file": filename})
    return result.deleted_count


async def get_all_source_files() -> List[Dict[str, Any]]:
    """
    Get a summary of all uploaded source files.
    
    Returns:
        List of documents with filename and chunk count
    """
    collection = get_knowledge_base_collection()
    
    pipeline = [
        {
            "$group": {
                "_id": "$source_file",
                "chunk_count": {"$sum": 1},
                "subject": {"$first": "$subject"},
                "language": {"$first": "$language"},
                "uploaded_at": {"$min": "$created_at"}
            }
        },
        {
            "$project": {
                "filename": "$_id",
                "chunk_count": 1,
                "subject": 1,
                "language": 1,
                "uploaded_at": 1,
                "_id": 0
            }
        },
        {"$sort": {"uploaded_at": -1}}
    ]
    
    results = []
    async for doc in collection.aggregate(pipeline):
        results.append(doc)
    
    return results


async def get_knowledge_base_stats() -> Dict[str, Any]:
    """Get statistics about the knowledge base."""
    collection = get_knowledge_base_collection()
    
    total_chunks = await collection.count_documents({})
    
    # Get counts by subject
    subject_pipeline = [
        {"$group": {"_id": "$subject", "count": {"$sum": 1}}}
    ]
    subjects = {}
    async for doc in collection.aggregate(subject_pipeline):
        subjects[doc["_id"]] = doc["count"]
    
    # Get counts by language
    language_pipeline = [
        {"$group": {"_id": "$language", "count": {"$sum": 1}}}
    ]
    languages = {}
    async for doc in collection.aggregate(language_pipeline):
        languages[doc["_id"]] = doc["count"]
    
    # Get unique source files count
    files_pipeline = [
        {"$group": {"_id": "$source_file"}},
        {"$count": "total"}
    ]
    files_result = await collection.aggregate(files_pipeline).to_list(1)
    unique_files = files_result[0]["total"] if files_result else 0
    
    return {
        "total_chunks": total_chunks,
        "unique_files": unique_files,
        "by_subject": subjects,
        "by_language": languages
    }
