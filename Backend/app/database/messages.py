"""
Messages Database Operations - DynamoDB
========================================
CRUD operations for the messages table.

DynamoDB Table: digimasterji-messages
- Partition Key: conversationId (String)
- Sort Key: messageId (String) - timestamp-prefixed UUID for ordering
- GSI: profileId-timestamp-index (for fetching messages by profile)

DigiMasterJi - AWS Migration
"""

from typing import Optional, List
from datetime import datetime, timedelta
from boto3.dynamodb.conditions import Key, Attr

from app.models.message import MessageCreate, MessageInDB
from app.database.dynamo import (
    get_table,
    generate_timestamp_id,
    TABLE_MESSAGES,
    datetime_to_iso,
    iso_to_datetime,
    serialize_for_dynamo,
    deserialize_from_dynamo
)


class MessagesDatabase:
    """Database operations for messages table."""
    
    TABLE_NAME = TABLE_MESSAGES
    
    @staticmethod
    def get_table():
        """Get messages table."""
        return get_table(MessagesDatabase.TABLE_NAME)
    
    @staticmethod
    def _item_to_message(item: dict) -> MessageInDB:
        """Convert DynamoDB item to MessageInDB model."""
        item = deserialize_from_dynamo(item)
        
        return MessageInDB(
            _id=item.get("messageId"),
            conversation_id=item.get("conversationId"),
            profile_id=item.get("profileId"),
            role=item.get("role"),
            content=item.get("content"),
            content_translated=item.get("content_translated"),
            audio_url=item.get("audio_url"),
            timestamp=iso_to_datetime(item.get("timestamp")),
            rag_references=item.get("rag_references", []),
            audio_base64=item.get("audio_base64"),
            audio_format=item.get("audio_format"),
            audio_language=item.get("audio_language"),
            audio_language_name=item.get("audio_language_name")
        )
    
    @staticmethod
    async def create_message(
        conversation_id: str,
        profile_id: str,
        message_data: MessageCreate
    ) -> MessageInDB:
        """
        Create a new message in a conversation.
        
        Args:
            conversation_id: Conversation's ID as string
            profile_id: Student profile ID
            message_data: Message creation data
            
        Returns:
            MessageInDB: Created message document
        """
        if not conversation_id:
            raise ValueError("Invalid conversation_id")
        if not profile_id:
            raise ValueError("Invalid profile_id")
            
        table = MessagesDatabase.get_table()
        
        # Use timestamp-prefixed UUID for natural ordering
        message_id = generate_timestamp_id()
        now = datetime.utcnow()
        
        item = {
            "conversationId": conversation_id,
            "messageId": message_id,
            "profileId": profile_id,
            "role": message_data.role,
            "content": message_data.content,
            "content_translated": message_data.content_translated,
            "audio_url": message_data.audio_url,
            "timestamp": datetime_to_iso(now),
            "rag_references": []
        }
        
        table.put_item(Item=serialize_for_dynamo(item))
        
        return MessagesDatabase._item_to_message(item)
    
    @staticmethod
    async def get_message_by_id(message_id: str) -> Optional[MessageInDB]:
        """
        Get message by ID using GSI.
        
        Args:
            message_id: Message's ID as string
            
        Returns:
            MessageInDB or None
        """
        if not message_id:
            return None
            
        table = MessagesDatabase.get_table()
        
        # Query using GSI on messageId
        response = table.query(
            IndexName="messageId-index",
            KeyConditionExpression=Key("messageId").eq(message_id)
        )
        
        items = response.get("Items", [])
        if items:
            return MessagesDatabase._item_to_message(items[0])
        return None
    
    @staticmethod
    async def get_messages_by_conversation(
        conversation_id: str,
        limit: Optional[int] = None
    ) -> List[MessageInDB]:
        """
        Get all messages for a conversation.
        
        Args:
            conversation_id: Conversation's ID as string
            limit: Optional limit on number of messages
            
        Returns:
            List of MessageInDB sorted by timestamp ascending
        """
        if not conversation_id:
            return []
            
        table = MessagesDatabase.get_table()
        
        query_params = {
            "KeyConditionExpression": Key("conversationId").eq(conversation_id),
            "ScanIndexForward": True  # Ascending order by sort key
        }
        
        if limit:
            # For limit, we query in reverse and take last N
            query_params["ScanIndexForward"] = False
            query_params["Limit"] = limit
        
        response = table.query(**query_params)
        items = response.get("Items", [])
        
        # Handle pagination for large conversations
        while "LastEvaluatedKey" in response and (limit is None or len(items) < limit):
            response = table.query(
                **query_params,
                ExclusiveStartKey=response["LastEvaluatedKey"]
            )
            items.extend(response.get("Items", []))
        
        # Sort by messageId (which is timestamp-prefixed) for chronological order
        items.sort(key=lambda x: x.get("messageId", ""))
        
        if limit:
            items = items[-limit:]  # Take last N messages
        
        messages = []
        for item in items:
            messages.append(MessagesDatabase._item_to_message(item))
        
        return messages
    
    @staticmethod
    async def get_recent_messages_by_profile(
        profile_id: str,
        limit: int = 50
    ) -> List[MessageInDB]:
        """
        Get recent messages for a profile across all conversations.
        
        Args:
            profile_id: Student profile ID
            limit: Maximum number of messages to return
            
        Returns:
            List of MessageInDB
        """
        if not profile_id:
            return []
            
        table = MessagesDatabase.get_table()
        
        # Query using GSI on profileId
        response = table.query(
            IndexName="profileId-timestamp-index",
            KeyConditionExpression=Key("profileId").eq(profile_id),
            ScanIndexForward=False,  # Most recent first
            Limit=limit
        )
        
        messages = []
        for item in response.get("Items", []):
            messages.append(MessagesDatabase._item_to_message(item))
        
        return messages
    
    @staticmethod
    async def count_messages_by_conversation(conversation_id: str) -> int:
        """
        Count messages in a conversation.
        
        Args:
            conversation_id: Conversation's ID as string
            
        Returns:
            Count of messages
        """
        if not conversation_id:
            return 0
            
        table = MessagesDatabase.get_table()
        
        response = table.query(
            KeyConditionExpression=Key("conversationId").eq(conversation_id),
            Select="COUNT"
        )
        
        return response.get("Count", 0)
    
    @staticmethod
    async def delete_messages_by_conversation(conversation_id: str) -> int:
        """
        Delete all messages in a conversation.
        
        Args:
            conversation_id: Conversation's ID as string
            
        Returns:
            Number of messages deleted
        """
        if not conversation_id:
            return 0
            
        table = MessagesDatabase.get_table()
        
        # First get all messages
        response = table.query(
            KeyConditionExpression=Key("conversationId").eq(conversation_id),
            ProjectionExpression="conversationId, messageId"
        )
        
        deleted_count = 0
        
        # Delete each message
        with table.batch_writer() as batch:
            for item in response.get("Items", []):
                batch.delete_item(
                    Key={
                        "conversationId": item["conversationId"],
                        "messageId": item["messageId"]
                    }
                )
                deleted_count += 1
        
        return deleted_count
    
    @staticmethod
    async def update_message_rag_references(
        message_id: str,
        rag_references: List[str]
    ) -> Optional[MessageInDB]:
        """
        Update RAG references for a message.
        
        Args:
            message_id: Message's ID as string
            rag_references: List of knowledge base IDs as strings
            
        Returns:
            Updated MessageInDB or None
        """
        if not message_id:
            return None
        
        message = await MessagesDatabase.get_message_by_id(message_id)
        if not message:
            return None
            
        table = MessagesDatabase.get_table()
        
        try:
            response = table.update_item(
                Key={"conversationId": str(message.conversation_id), "messageId": message_id},
                UpdateExpression="SET rag_references = :refs",
                ExpressionAttributeValues={":refs": rag_references},
                ReturnValues="ALL_NEW"
            )
            return MessagesDatabase._item_to_message(response.get("Attributes", {}))
        except Exception:
            return None
    
    @staticmethod
    async def update_message_tts_audio(
        message_id: str,
        audio_base64: str,
        audio_format: str,
        audio_language: str,
        audio_language_name: str
    ) -> Optional[MessageInDB]:
        """
        Update TTS audio fields for a message.
        
        Args:
            message_id: Message's ID as string
            audio_base64: Base64 encoded audio data
            audio_format: Audio format (e.g., 'mp3')
            audio_language: Language code (e.g., 'hi')
            audio_language_name: Human-readable language name
            
        Returns:
            Updated MessageInDB or None
        """
        if not message_id:
            return None
        
        message = await MessagesDatabase.get_message_by_id(message_id)
        if not message:
            return None
            
        table = MessagesDatabase.get_table()
        
        try:
            response = table.update_item(
                Key={"conversationId": str(message.conversation_id), "messageId": message_id},
                UpdateExpression="SET audio_base64 = :audio, audio_format = :format, audio_language = :lang, audio_language_name = :lang_name",
                ExpressionAttributeValues={
                    ":audio": audio_base64,
                    ":format": audio_format,
                    ":lang": audio_language,
                    ":lang_name": audio_language_name
                },
                ReturnValues="ALL_NEW"
            )
            return MessagesDatabase._item_to_message(response.get("Attributes", {}))
        except Exception:
            return None
    
    @staticmethod
    async def get_messages_for_sync(
        conversation_id: str,
        days: int = 15
    ) -> List[dict]:
        """
        Get messages for sync (past N days, without audio fields).
        
        Args:
            conversation_id: Conversation's ID as string
            days: Number of days to look back (default 15)
            
        Returns:
            List of message dicts without audio fields
        """
        if not conversation_id:
            return []
            
        table = MessagesDatabase.get_table()
        
        # Calculate cutoff date
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        cutoff_iso = datetime_to_iso(cutoff_date)
        
        # Query messages
        response = table.query(
            KeyConditionExpression=Key("conversationId").eq(conversation_id),
            FilterExpression=Attr("timestamp").gte(cutoff_iso),
            ScanIndexForward=True
        )
        
        messages = []
        for item in response.get("Items", []):
            item = deserialize_from_dynamo(item)
            # Exclude audio fields
            messages.append({
                "_id": item.get("messageId"),
                "conversation_id": item.get("conversationId"),
                "profile_id": item.get("profileId"),
                "role": item.get("role"),
                "content": item.get("content"),
                "content_translated": item.get("content_translated"),
                "timestamp": iso_to_datetime(item.get("timestamp")),
                "rag_references": item.get("rag_references", [])
            })
        
        return messages
