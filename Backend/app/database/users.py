"""
Users Database Operations - DynamoDB
=====================================
CRUD operations for the users (master accounts) table.

DynamoDB Table: digimasterji-users
- Partition Key: userId (String)

DigiMasterJi - AWS Migration
"""

from typing import Optional, List
from datetime import datetime
from boto3.dynamodb.conditions import Key, Attr

from app.models.user import UserCreate, UserInDB, UserUpdate, UserSettings
from app.database.dynamo import (
    get_table, 
    generate_id, 
    TABLE_USERS,
    datetime_to_iso,
    iso_to_datetime,
    serialize_for_dynamo,
    deserialize_from_dynamo
)


class UsersDatabase:
    """Database operations for users table."""
    
    TABLE_NAME = TABLE_USERS
    
    @staticmethod
    def get_table():
        """Get users table."""
        return get_table(UsersDatabase.TABLE_NAME)
    
    @staticmethod
    def _item_to_user(item: dict) -> UserInDB:
        """Convert DynamoDB item to UserInDB model."""
        item = deserialize_from_dynamo(item)
        
        # Map DynamoDB fields to model fields
        # Note: DynamoDB uses 'phone' (GSI key), model uses 'phone_number'
        return UserInDB(
            _id=item.get("userId"),
            email=item.get("email"),
            phone_number=item.get("phone"),
            full_name=item.get("full_name"),
            password_hash=item.get("password_hash"),
            registered_at=iso_to_datetime(item.get("registered_at")),
            last_login=iso_to_datetime(item.get("last_login")),
            settings=UserSettings(**item.get("settings", {})) if item.get("settings") else None,
            refresh_token=item.get("refresh_token"),
            refresh_token_expires=iso_to_datetime(item.get("refresh_token_expires"))
        )
    
    @staticmethod
    async def create_user(user_data: UserCreate, password_hash: str) -> UserInDB:
        """
        Create a new user in the database.
        
        Args:
            user_data: User creation data
            password_hash: Hashed password
            
        Returns:
            UserInDB: Created user document
        """
        table = UsersDatabase.get_table()
        
        user_id = generate_id()
        now = datetime.utcnow()
        
        item = {
            "userId": user_id,
            "email": user_data.email.lower(),
            "phone": user_data.phone_number,  # GSI key is 'phone'
            "full_name": user_data.full_name,
            "password_hash": password_hash,
            "registered_at": datetime_to_iso(now),
            "last_login": None,
            "settings": {
                "sync_enabled": True,
                "data_saver_mode": True
            }
        }
        
        table.put_item(Item=serialize_for_dynamo(item))
        
        return UsersDatabase._item_to_user(item)
    
    @staticmethod
    async def get_user_by_id(user_id: str) -> Optional[UserInDB]:
        """
        Get user by ID.
        
        Args:
            user_id: User's ID as string
            
        Returns:
            UserInDB or None
        """
        if not user_id:
            return None
            
        table = UsersDatabase.get_table()
        
        response = table.get_item(Key={"userId": user_id})
        item = response.get("Item")
        
        if item:
            return UsersDatabase._item_to_user(item)
        return None
    
    @staticmethod
    async def get_user_by_email(email: str) -> Optional[UserInDB]:
        """
        Get user by email address.
        Uses GSI: email-index
        
        Args:
            email: User's email
            
        Returns:
            UserInDB or None
        """
        table = UsersDatabase.get_table()
        
        # Query using GSI on email
        response = table.query(
            IndexName="email-index",
            KeyConditionExpression=Key("email").eq(email.lower())
        )
        
        items = response.get("Items", [])
        if items:
            return UsersDatabase._item_to_user(items[0])
        return None
    
    @staticmethod
    async def get_user_by_phone(phone_number: str) -> Optional[UserInDB]:
        """
        Get user by phone number.
        Uses GSI: phone-index
        
        Args:
            phone_number: User's phone number
            
        Returns:
            UserInDB or None
        """
        table = UsersDatabase.get_table()
        
        # Query using GSI on phone (GSI key is 'phone', not 'phone_number')
        response = table.query(
            IndexName="phone-index",
            KeyConditionExpression=Key("phone").eq(phone_number)
        )
        
        items = response.get("Items", [])
        if items:
            return UsersDatabase._item_to_user(items[0])
        return None
    
    @staticmethod
    async def update_user(user_id: str, user_update: UserUpdate) -> Optional[UserInDB]:
        """
        Update user information.
        
        Args:
            user_id: User's ID as string
            user_update: Fields to update
            
        Returns:
            Updated UserInDB or None
        """
        if not user_id:
            return None
            
        table = UsersDatabase.get_table()
        
        # Build update expression
        update_parts = []
        expression_values = {}
        expression_names = {}
        
        if user_update.email is not None:
            update_parts.append("#email = :email")
            expression_values[":email"] = user_update.email.lower()
            expression_names["#email"] = "email"
            
        if user_update.phone_number is not None:
            update_parts.append("phone = :phone")  # GSI key is 'phone'
            expression_values[":phone"] = user_update.phone_number
            
        if user_update.full_name is not None:
            update_parts.append("full_name = :name")
            expression_values[":name"] = user_update.full_name
            
        if user_update.settings is not None:
            update_parts.append("settings = :settings")
            expression_values[":settings"] = serialize_for_dynamo(user_update.settings.model_dump())
        
        if not update_parts:
            return await UsersDatabase.get_user_by_id(user_id)
        
        update_expression = "SET " + ", ".join(update_parts)
        
        try:
            kwargs = {
                "Key": {"userId": user_id},
                "UpdateExpression": update_expression,
                "ExpressionAttributeValues": expression_values,
                "ReturnValues": "ALL_NEW"
            }
            if expression_names:
                kwargs["ExpressionAttributeNames"] = expression_names
                
            response = table.update_item(**kwargs)
            return UsersDatabase._item_to_user(response.get("Attributes", {}))
        except Exception:
            return None
    
    @staticmethod
    async def update_last_login(user_id: str) -> bool:
        """
        Update user's last login timestamp.
        
        Args:
            user_id: User's ID as string
            
        Returns:
            True if successful, False otherwise
        """
        if not user_id:
            return False
            
        table = UsersDatabase.get_table()
        
        try:
            table.update_item(
                Key={"userId": user_id},
                UpdateExpression="SET last_login = :login",
                ExpressionAttributeValues={":login": datetime_to_iso(datetime.utcnow())}
            )
            return True
        except Exception:
            return False
    
    @staticmethod
    async def delete_user(user_id: str) -> bool:
        """
        Delete a user from the database.
        
        Args:
            user_id: User's ID as string
            
        Returns:
            True if deleted, False otherwise
        """
        if not user_id:
            return False
            
        table = UsersDatabase.get_table()
        
        try:
            table.delete_item(Key={"userId": user_id})
            return True
        except Exception:
            return False
    
    @staticmethod
    async def email_exists(email: str) -> bool:
        """
        Check if email already exists.
        
        Args:
            email: Email to check
            
        Returns:
            True if exists, False otherwise
        """
        user = await UsersDatabase.get_user_by_email(email)
        return user is not None
    
    @staticmethod
    async def phone_exists(phone_number: str) -> bool:
        """
        Check if phone number already exists.
        
        Args:
            phone_number: Phone number to check
            
        Returns:
            True if exists, False otherwise
        """
        user = await UsersDatabase.get_user_by_phone(phone_number)
        return user is not None
    
    @staticmethod
    async def update_refresh_token(user_id: str, refresh_token: str, expires_at: datetime) -> bool:
        """
        Update user's refresh token in the database.
        
        Args:
            user_id: User's ID as string
            refresh_token: New refresh token
            expires_at: Token expiration datetime
            
        Returns:
            True if updated, False otherwise
        """
        if not user_id:
            return False
            
        table = UsersDatabase.get_table()
        
        try:
            table.update_item(
                Key={"userId": user_id},
                UpdateExpression="SET refresh_token = :token, refresh_token_expires = :expires",
                ExpressionAttributeValues={
                    ":token": refresh_token,
                    ":expires": datetime_to_iso(expires_at)
                }
            )
            return True
        except Exception:
            return False
    
    @staticmethod
    async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
        """
        Verify if the provided refresh token matches the stored one and is not expired.
        
        Args:
            user_id: User's ID as string
            refresh_token: Refresh token to verify
            
        Returns:
            True if valid, False otherwise
        """
        if not user_id:
            return False
            
        user = await UsersDatabase.get_user_by_id(user_id)
        if not user:
            return False
        
        if user.refresh_token != refresh_token:
            return False
        
        if user.refresh_token_expires and user.refresh_token_expires < datetime.utcnow():
            return False
        
        return True
    
    @staticmethod
    async def clear_refresh_token(user_id: str) -> bool:
        """
        Clear user's refresh token (used during logout).
        
        Args:
            user_id: User's ID as string
            
        Returns:
            True if cleared, False otherwise
        """
        if not user_id:
            return False
            
        table = UsersDatabase.get_table()
        
        try:
            table.update_item(
                Key={"userId": user_id},
                UpdateExpression="SET refresh_token = :token, refresh_token_expires = :expires",
                ExpressionAttributeValues={
                    ":token": None,
                    ":expires": None
                }
            )
            return True
        except Exception:
            return False
