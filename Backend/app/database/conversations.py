"""
Conversations Database Operations - DynamoDB
=============================================
CRUD operations for the conversations table.

DynamoDB Table: digimasterji-conversations
- Partition Key: profileId (String)
- Sort Key: conversationId (String)

DigiMasterJi - AWS Migration
"""

from typing import Optional, List
from datetime import datetime
from boto3.dynamodb.conditions import Key

from app.models.conversation import ConversationCreate, ConversationInDB, ConversationUpdate
from app.database.dynamo import (
    get_table,
    generate_id,
    TABLE_CONVERSATIONS,
    datetime_to_iso,
    iso_to_datetime,
    serialize_for_dynamo,
    deserialize_from_dynamo
)


class ConversationsDatabase:
    """Database operations for conversations table."""
    
    TABLE_NAME = TABLE_CONVERSATIONS
    
    @staticmethod
    def get_table():
        """Get conversations table."""
        return get_table(ConversationsDatabase.TABLE_NAME)
    
    @staticmethod
    def _item_to_conversation(item: dict) -> ConversationInDB:
        """Convert DynamoDB item to ConversationInDB model."""
        item = deserialize_from_dynamo(item)
        
        return ConversationInDB(
            _id=item.get("conversationId"),
            profile_id=item.get("profileId"),
            title=item.get("title"),
            subject_tag=item.get("subject_tag"),
            created_at=iso_to_datetime(item.get("created_at")),
            updated_at=iso_to_datetime(item.get("updated_at"))
        )
    
    @staticmethod
    async def create_conversation(
        profile_id: str,
        conversation_data: ConversationCreate
    ) -> ConversationInDB:
        """
        Create a new conversation.
        
        Args:
            profile_id: Student profile ID
            conversation_data: Conversation creation data
            
        Returns:
            ConversationInDB: Created conversation document
        """
        if not profile_id:
            raise ValueError("Invalid profile_id")
            
        table = ConversationsDatabase.get_table()
        
        conversation_id = generate_id()
        now = datetime.utcnow()
        
        title = conversation_data.topic if conversation_data.topic else "New Conversation"
        
        item = {
            "profileId": profile_id,
            "conversationId": conversation_id,
            "title": title,
            "subject_tag": None,
            "created_at": datetime_to_iso(now),
            "updated_at": datetime_to_iso(now)
        }
        
        table.put_item(Item=serialize_for_dynamo(item))
        
        return ConversationsDatabase._item_to_conversation(item)
    
    @staticmethod
    async def get_conversation_by_id(conversation_id: str) -> Optional[ConversationInDB]:
        """
        Get conversation by ID using GSI.
        
        Args:
            conversation_id: Conversation's ID as string
            
        Returns:
            ConversationInDB or None
        """
        if not conversation_id:
            return None
            
        table = ConversationsDatabase.get_table()
        
        # Query using GSI on conversationId
        response = table.query(
            IndexName="conversationId-index",
            KeyConditionExpression=Key("conversationId").eq(conversation_id)
        )
        
        items = response.get("Items", [])
        if items:
            return ConversationsDatabase._item_to_conversation(items[0])
        return None
    
    @staticmethod
    async def get_conversations_by_profile(
        profile_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[ConversationInDB]:
        """
        Get all conversations for a profile with pagination.
        
        Args:
            profile_id: Student profile ID
            limit: Maximum number of conversations to return
            offset: Number of conversations to skip
            
        Returns:
            List of ConversationInDB
        """
        if not profile_id:
            return []
            
        table = ConversationsDatabase.get_table()
        
        # Query all conversations for profile
        response = table.query(
            KeyConditionExpression=Key("profileId").eq(profile_id),
            ScanIndexForward=False  # Sort by sort key descending
        )
        
        items = response.get("Items", [])
        
        # Sort by updated_at descending (most recent first)
        items.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        
        # Apply offset and limit
        paginated_items = items[offset:offset + limit]
        
        conversations = []
        for item in paginated_items:
            conversations.append(ConversationsDatabase._item_to_conversation(item))
        
        return conversations
    
    @staticmethod
    async def update_conversation(
        conversation_id: str,
        conversation_update: ConversationUpdate
    ) -> Optional[ConversationInDB]:
        """
        Update conversation metadata.
        
        Args:
            conversation_id: Conversation's ID as string
            conversation_update: Fields to update
            
        Returns:
            Updated ConversationInDB or None
        """
        if not conversation_id:
            return None
        
        # First get the conversation to get profileId
        conversation = await ConversationsDatabase.get_conversation_by_id(conversation_id)
        if not conversation:
            return None
            
        table = ConversationsDatabase.get_table()
        
        # Build update expression
        update_parts = ["updated_at = :updated_at"]
        expression_values = {":updated_at": datetime_to_iso(datetime.utcnow())}
        
        if conversation_update.title is not None:
            update_parts.append("title = :title")
            expression_values[":title"] = conversation_update.title
            
        if conversation_update.subject_tag is not None:
            update_parts.append("subject_tag = :tag")
            expression_values[":tag"] = conversation_update.subject_tag
        
        update_expression = "SET " + ", ".join(update_parts)
        
        try:
            response = table.update_item(
                Key={"profileId": str(conversation.profile_id), "conversationId": conversation_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ReturnValues="ALL_NEW"
            )
            return ConversationsDatabase._item_to_conversation(response.get("Attributes", {}))
        except Exception:
            return None
    
    @staticmethod
    async def update_conversation_timestamp(conversation_id: str) -> bool:
        """
        Update conversation's updated_at timestamp.
        
        Args:
            conversation_id: Conversation's ID as string
            
        Returns:
            True if successful, False otherwise
        """
        if not conversation_id:
            return False
        
        conversation = await ConversationsDatabase.get_conversation_by_id(conversation_id)
        if not conversation:
            return False
            
        table = ConversationsDatabase.get_table()
        
        try:
            table.update_item(
                Key={"profileId": str(conversation.profile_id), "conversationId": conversation_id},
                UpdateExpression="SET updated_at = :updated",
                ExpressionAttributeValues={":updated": datetime_to_iso(datetime.utcnow())}
            )
            return True
        except Exception:
            return False
    
    @staticmethod
    async def delete_conversation(conversation_id: str) -> bool:
        """
        Delete a conversation.
        
        Args:
            conversation_id: Conversation's ID as string
            
        Returns:
            True if deleted, False otherwise
        """
        if not conversation_id:
            return False
        
        conversation = await ConversationsDatabase.get_conversation_by_id(conversation_id)
        if not conversation:
            return False
            
        table = ConversationsDatabase.get_table()
        
        try:
            table.delete_item(
                Key={"profileId": str(conversation.profile_id), "conversationId": conversation_id}
            )
            return True
        except Exception:
            return False
    
    @staticmethod
    async def count_conversations_by_profile(profile_id: str) -> int:
        """
        Count conversations for a profile.
        
        Args:
            profile_id: Student profile ID
            
        Returns:
            Count of conversations
        """
        if not profile_id:
            return 0
            
        table = ConversationsDatabase.get_table()
        
        response = table.query(
            KeyConditionExpression=Key("profileId").eq(profile_id),
            Select="COUNT"
        )
        
        return response.get("Count", 0)
