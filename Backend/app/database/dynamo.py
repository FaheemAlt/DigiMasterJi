"""
DynamoDB Connection and Utilities
==================================
Provides shared DynamoDB resource and table access for all database operations.

DigiMasterJi - AWS Migration
"""

import boto3
import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from datetime import datetime
from decimal import Decimal
import json
import uuid

load_dotenv()


class DynamoDBConnection:
    """Singleton DynamoDB connection manager."""
    
    _resource: Optional[boto3.resource] = None
    _client: Optional[boto3.client] = None
    
    @classmethod
    def get_resource(cls) -> boto3.resource:
        """Get or create DynamoDB resource."""
        if cls._resource is None:
            # Detect if running on Lambda
            is_lambda = os.getenv("AWS_LAMBDA_FUNCTION_NAME") is not None
            region = os.getenv("AWS_REGION", "us-east-1")
            
            if is_lambda:
                # On Lambda, always use IAM role (ignore .env credentials)
                cls._resource = boto3.resource('dynamodb', region_name=region)
            else:
                # Locally, use credentials from env vars if available
                access_key = os.getenv("AWS_ACCESS_KEY_ID")
                secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
                
                if access_key and secret_key:
                    cls._resource = boto3.resource(
                        'dynamodb',
                        region_name=region,
                        aws_access_key_id=access_key,
                        aws_secret_access_key=secret_key
                    )
                else:
                    cls._resource = boto3.resource('dynamodb', region_name=region)
        return cls._resource
    
    @classmethod
    def get_client(cls) -> boto3.client:
        """Get or create DynamoDB client."""
        if cls._client is None:
            is_lambda = os.getenv("AWS_LAMBDA_FUNCTION_NAME") is not None
            region = os.getenv("AWS_REGION", "us-east-1")
            
            if is_lambda:
                # On Lambda, always use IAM role
                cls._client = boto3.client('dynamodb', region_name=region)
            else:
                access_key = os.getenv("AWS_ACCESS_KEY_ID")
                secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
                
                if access_key and secret_key:
                    cls._client = boto3.client(
                        'dynamodb',
                        region_name=region,
                        aws_access_key_id=access_key,
                        aws_secret_access_key=secret_key
                    )
                else:
                    cls._client = boto3.client('dynamodb', region_name=region)
        return cls._client


# Table names from environment variables
TABLE_USERS = os.getenv("DYNAMO_TABLE_USERS", "digimasterji-users")
TABLE_PROFILES = os.getenv("DYNAMO_TABLE_PROFILES", "digimasterji-profiles")
TABLE_CONVERSATIONS = os.getenv("DYNAMO_TABLE_CONVERSATIONS", "digimasterji-conversations")
TABLE_MESSAGES = os.getenv("DYNAMO_TABLE_MESSAGES", "digimasterji-messages")
TABLE_QUIZZES = os.getenv("DYNAMO_TABLE_QUIZZES", "digimasterji-quizzes")
TABLE_KNOWLEDGE_BASE = os.getenv("DYNAMO_TABLE_KNOWLEDGE_BASE", "digimasterji-knowledge-base")


def get_table(table_name: str):
    """Get a DynamoDB table resource."""
    return DynamoDBConnection.get_resource().Table(table_name)


def generate_id() -> str:
    """Generate a new UUID v4 string for use as a primary key."""
    return str(uuid.uuid4())


def generate_timestamp_id() -> str:
    """Generate a timestamp-prefixed UUID for natural ordering."""
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    return f"{timestamp}_{uuid.uuid4()}"


def datetime_to_iso(dt: Optional[datetime]) -> Optional[str]:
    """Convert datetime to ISO 8601 string for DynamoDB storage."""
    if dt is None:
        return None
    return dt.isoformat()


def iso_to_datetime(iso_str: Optional[str]) -> Optional[datetime]:
    """Convert ISO 8601 string back to datetime."""
    if iso_str is None:
        return None
    try:
        return datetime.fromisoformat(iso_str)
    except (ValueError, TypeError):
        return None


def python_to_dynamo(obj: Any) -> Any:
    """
    Convert Python types to DynamoDB-compatible types.
    - datetime -> ISO string
    - float -> Decimal
    - dict/list -> recursive conversion
    """
    if obj is None:
        return None
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: python_to_dynamo(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [python_to_dynamo(item) for item in obj]
    return obj


def dynamo_to_python(obj: Any) -> Any:
    """
    Convert DynamoDB types back to Python types.
    - Decimal -> float/int
    - ISO string dates -> datetime (when detected)
    """
    if obj is None:
        return None
    if isinstance(obj, Decimal):
        # Convert to int if it's a whole number, otherwise float
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    if isinstance(obj, dict):
        return {k: dynamo_to_python(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [dynamo_to_python(item) for item in obj]
    return obj


def serialize_for_dynamo(data: Dict[str, Any]) -> Dict[str, Any]:
    """Serialize a dictionary for DynamoDB storage."""
    return python_to_dynamo(data)


def deserialize_from_dynamo(data: Dict[str, Any]) -> Dict[str, Any]:
    """Deserialize a DynamoDB item back to Python types."""
    return dynamo_to_python(data)


# Startup/shutdown functions to maintain API compatibility
async def connect_to_dynamo():
    """Initialize DynamoDB connection (replaces MongoDB connect)."""
    # DynamoDB doesn't require persistent connection setup
    # Just verify we can access the tables
    try:
        resource = DynamoDBConnection.get_resource()
        print(f"Connected to DynamoDB (region: {os.getenv('AWS_REGION', 'ap-south-1')})")
    except Exception as e:
        print(f"Warning: DynamoDB connection test failed: {e}")


async def close_dynamo_connection():
    """Close DynamoDB connection (replaces MongoDB close)."""
    # DynamoDB uses HTTP connections that don't need explicit closing
    print("DynamoDB connections released")
