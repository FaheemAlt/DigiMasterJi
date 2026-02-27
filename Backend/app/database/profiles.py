"""
Profiles Database Operations - DynamoDB
========================================
CRUD operations for the student profiles table.

DynamoDB Table: digimasterji-profiles
- Partition Key: userId (String)
- Sort Key: profileId (String)
- GSI: profileId-index (Partition Key: profileId)

DigiMasterJi - AWS Migration
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date
from boto3.dynamodb.conditions import Key, Attr

from app.models.profile import ProfileCreate, ProfileInDB, ProfileUpdate, Gamification, LearningPreferences, StoredLearningInsights
from app.database.dynamo import (
    get_table,
    generate_id,
    TABLE_PROFILES,
    datetime_to_iso,
    iso_to_datetime,
    serialize_for_dynamo,
    deserialize_from_dynamo
)


class ProfilesDatabase:
    """Database operations for profiles table."""
    
    TABLE_NAME = TABLE_PROFILES
    
    @staticmethod
    def get_table():
        """Get profiles table."""
        return get_table(ProfilesDatabase.TABLE_NAME)
    
    @staticmethod
    def _item_to_profile(item: dict) -> ProfileInDB:
        """Convert DynamoDB item to ProfileInDB model."""
        item = deserialize_from_dynamo(item)
        
        # Parse gamification
        gamification_data = item.get("gamification", {})
        gamification = Gamification(
            xp=gamification_data.get("xp", 0),
            current_streak_days=gamification_data.get("current_streak_days", 0),
            last_activity_date=iso_to_datetime(gamification_data.get("last_activity_date")),
            badges=gamification_data.get("badges", [])
        )
        
        # Parse learning preferences
        learning_prefs_data = item.get("learning_preferences", {})
        learning_preferences = LearningPreferences(
            voice_enabled=learning_prefs_data.get("voice_enabled", True)
        )
        
        # Parse learning insights if present
        learning_insights = None
        if item.get("learning_insights"):
            insights_data = item["learning_insights"]
            learning_insights = StoredLearningInsights(
                overall_assessment=insights_data.get("overall_assessment"),
                subject_insights=insights_data.get("subject_insights", []),
                weak_topics_explanation=insights_data.get("weak_topics_explanation", []),
                strengths=insights_data.get("strengths", []),
                weekly_goals=insights_data.get("weekly_goals", []),
                motivation_message=insights_data.get("motivation_message"),
                generated_at=iso_to_datetime(insights_data.get("generated_at"))
            )
        
        return ProfileInDB(
            _id=item.get("profileId"),
            master_user_id=item.get("userId"),
            name=item.get("name"),
            age=item.get("age"),
            grade_level=item.get("grade_level"),
            preferred_language=item.get("preferred_language"),
            avatar=item.get("avatar", "default_avatar.png"),
            gamification=gamification,
            learning_preferences=learning_preferences,
            learning_insights=learning_insights,
            created_at=iso_to_datetime(item.get("created_at")),
            updated_at=iso_to_datetime(item.get("updated_at"))
        )
    
    @staticmethod
    async def create_profile(master_user_id: str, profile_data: ProfileCreate) -> ProfileInDB:
        """
        Create a new student profile.
        
        Args:
            master_user_id: Parent/Teacher's user ID
            profile_data: Profile creation data
            
        Returns:
            ProfileInDB: Created profile document
        """
        if not master_user_id:
            raise ValueError("Invalid master_user_id")
            
        table = ProfilesDatabase.get_table()
        
        profile_id = generate_id()
        now = datetime.utcnow()
        
        item = {
            "userId": master_user_id,
            "profileId": profile_id,
            "name": profile_data.name,
            "age": profile_data.age,
            "grade_level": profile_data.grade_level,
            "preferred_language": profile_data.preferred_language,
            "avatar": profile_data.avatar or "default_avatar.png",
            "gamification": {
                "xp": 0,
                "current_streak_days": 0,
                "last_activity_date": None,
                "badges": []
            },
            "learning_preferences": {
                "voice_enabled": True
            },
            "created_at": datetime_to_iso(now),
            "updated_at": datetime_to_iso(now)
        }
        
        table.put_item(Item=serialize_for_dynamo(item))
        
        return ProfilesDatabase._item_to_profile(item)
    
    @staticmethod
    async def get_profile_by_id(profile_id: str) -> Optional[ProfileInDB]:
        """
        Get profile by ID using GSI.
        
        Args:
            profile_id: Profile's ID as string
            
        Returns:
            ProfileInDB or None
        """
        if not profile_id:
            return None
            
        table = ProfilesDatabase.get_table()
        
        # Query using GSI on profileId
        response = table.query(
            IndexName="profileId-index",
            KeyConditionExpression=Key("profileId").eq(profile_id)
        )
        
        items = response.get("Items", [])
        if items:
            return ProfilesDatabase._item_to_profile(items[0])
        return None
    
    @staticmethod
    async def get_profiles_by_user(master_user_id: str) -> List[ProfileInDB]:
        """
        Get all profiles for a master user.
        
        Args:
            master_user_id: Parent/Teacher's user ID
            
        Returns:
            List of ProfileInDB
        """
        if not master_user_id:
            return []
            
        table = ProfilesDatabase.get_table()
        
        response = table.query(
            KeyConditionExpression=Key("userId").eq(master_user_id)
        )
        
        profiles = []
        for item in response.get("Items", []):
            profiles.append(ProfilesDatabase._item_to_profile(item))
        
        return profiles
    
    @staticmethod
    async def update_profile(profile_id: str, profile_update: ProfileUpdate) -> Optional[ProfileInDB]:
        """
        Update profile information.
        
        Args:
            profile_id: Profile's ID as string
            profile_update: Fields to update
            
        Returns:
            Updated ProfileInDB or None
        """
        if not profile_id:
            return None
        
        # First get the profile to get the userId (partition key)
        profile = await ProfilesDatabase.get_profile_by_id(profile_id)
        if not profile:
            return None
            
        table = ProfilesDatabase.get_table()
        
        # Build update expression
        update_parts = ["updated_at = :updated_at"]
        expression_values = {":updated_at": datetime_to_iso(datetime.utcnow())}
        expression_names = {}
        
        if profile_update.name is not None:
            update_parts.append("#name = :name")
            expression_values[":name"] = profile_update.name
            expression_names["#name"] = "name"
            
        if profile_update.age is not None:
            update_parts.append("age = :age")
            expression_values[":age"] = profile_update.age
            
        if profile_update.grade_level is not None:
            update_parts.append("grade_level = :grade")
            expression_values[":grade"] = profile_update.grade_level
            
        if profile_update.preferred_language is not None:
            update_parts.append("preferred_language = :lang")
            expression_values[":lang"] = profile_update.preferred_language
            
        if profile_update.avatar is not None:
            update_parts.append("avatar = :avatar")
            expression_values[":avatar"] = profile_update.avatar
            
        if profile_update.learning_preferences is not None:
            update_parts.append("learning_preferences = :prefs")
            expression_values[":prefs"] = serialize_for_dynamo(profile_update.learning_preferences.model_dump())
        
        update_expression = "SET " + ", ".join(update_parts)
        
        try:
            kwargs = {
                "Key": {"userId": str(profile.master_user_id), "profileId": profile_id},
                "UpdateExpression": update_expression,
                "ExpressionAttributeValues": expression_values,
                "ReturnValues": "ALL_NEW"
            }
            if expression_names:
                kwargs["ExpressionAttributeNames"] = expression_names
                
            response = table.update_item(**kwargs)
            return ProfilesDatabase._item_to_profile(response.get("Attributes", {}))
        except Exception:
            return None
    
    @staticmethod
    async def delete_profile(profile_id: str) -> bool:
        """
        Delete a profile from the database.
        
        Args:
            profile_id: Profile's ID as string
            
        Returns:
            True if deleted, False otherwise
        """
        if not profile_id:
            return False
        
        # First get the profile to get the userId (partition key)
        profile = await ProfilesDatabase.get_profile_by_id(profile_id)
        if not profile:
            return False
            
        table = ProfilesDatabase.get_table()
        
        try:
            table.delete_item(
                Key={"userId": str(profile.master_user_id), "profileId": profile_id}
            )
            return True
        except Exception:
            return False
    
    @staticmethod
    async def update_gamification(
        profile_id: str,
        xp_delta: int = 0,
        streak_delta: int = 0,
        new_badges: Optional[List[str]] = None
    ) -> Optional[ProfileInDB]:
        """
        Update gamification stats for a profile.
        
        Args:
            profile_id: Profile's ID as string
            xp_delta: XP points to add (can be negative)
            streak_delta: Streak days to add/subtract
            new_badges: New badges to add
            
        Returns:
            Updated ProfileInDB or None
        """
        if not profile_id:
            return None
        
        profile = await ProfilesDatabase.get_profile_by_id(profile_id)
        if not profile:
            return None
            
        table = ProfilesDatabase.get_table()
        
        # Build update expression
        update_parts = [
            "gamification.last_activity_date = :last_activity",
            "updated_at = :updated_at"
        ]
        expression_values = {
            ":last_activity": datetime_to_iso(datetime.utcnow()),
            ":updated_at": datetime_to_iso(datetime.utcnow())
        }
        
        if xp_delta != 0:
            new_xp = profile.gamification.xp + xp_delta
            update_parts.append("gamification.xp = :xp")
            expression_values[":xp"] = new_xp
        
        if streak_delta != 0:
            new_streak = max(0, profile.gamification.current_streak_days + streak_delta)
            update_parts.append("gamification.current_streak_days = :streak")
            expression_values[":streak"] = new_streak
        
        if new_badges:
            current_badges = profile.gamification.badges or []
            updated_badges = list(set(current_badges + new_badges))
            update_parts.append("gamification.badges = :badges")
            expression_values[":badges"] = updated_badges
        
        update_expression = "SET " + ", ".join(update_parts)
        
        try:
            response = table.update_item(
                Key={"userId": str(profile.master_user_id), "profileId": profile_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ReturnValues="ALL_NEW"
            )
            return ProfilesDatabase._item_to_profile(response.get("Attributes", {}))
        except Exception:
            return None
    
    @staticmethod
    async def update_last_activity(profile_id: str) -> bool:
        """
        Update profile's last activity date.
        
        Args:
            profile_id: Profile's ID as string
            
        Returns:
            True if successful, False otherwise
        """
        if not profile_id:
            return False
        
        profile = await ProfilesDatabase.get_profile_by_id(profile_id)
        if not profile:
            return False
            
        table = ProfilesDatabase.get_table()
        
        try:
            table.update_item(
                Key={"userId": str(profile.master_user_id), "profileId": profile_id},
                UpdateExpression="SET gamification.last_activity_date = :last, updated_at = :updated",
                ExpressionAttributeValues={
                    ":last": datetime_to_iso(datetime.utcnow()),
                    ":updated": datetime_to_iso(datetime.utcnow())
                }
            )
            return True
        except Exception:
            return False
    
    @staticmethod
    async def count_profiles_by_user(master_user_id: str) -> int:
        """
        Count number of profiles for a master user.
        
        Args:
            master_user_id: Parent/Teacher's user ID
            
        Returns:
            Count of profiles
        """
        if not master_user_id:
            return 0
            
        table = ProfilesDatabase.get_table()
        
        response = table.query(
            KeyConditionExpression=Key("userId").eq(master_user_id),
            Select="COUNT"
        )
        
        return response.get("Count", 0)
    
    @staticmethod
    async def update_quiz_stats(
        profile_id: str,
        xp_earned: int,
        maintain_streak: bool
    ) -> Optional[ProfileInDB]:
        """
        Update profile after quiz completion (XP and streak).
        
        Args:
            profile_id: Profile's ID as string
            xp_earned: XP points earned from quiz
            maintain_streak: Whether the quiz was completed on time
            
        Returns:
            Updated ProfileInDB or None
        """
        if not profile_id:
            return None
        
        profile = await ProfilesDatabase.get_profile_by_id(profile_id)
        if not profile:
            return None
            
        table = ProfilesDatabase.get_table()
        
        # Calculate new XP
        new_xp = profile.gamification.xp + xp_earned
        
        # Handle streak logic
        from datetime import timedelta
        
        last_activity = profile.gamification.last_activity_date
        today = date.today()
        new_streak = profile.gamification.current_streak_days
        
        if maintain_streak:
            if last_activity:
                last_date = last_activity.date() if isinstance(last_activity, datetime) else last_activity
                days_diff = (today - last_date).days
                
                if days_diff == 1:
                    new_streak += 1
                elif days_diff == 0:
                    pass  # Same day
                else:
                    new_streak = 1
            else:
                new_streak = 1
        else:
            new_streak = 0
        
        try:
            response = table.update_item(
                Key={"userId": str(profile.master_user_id), "profileId": profile_id},
                UpdateExpression="SET gamification.xp = :xp, gamification.current_streak_days = :streak, gamification.last_activity_date = :last, updated_at = :updated",
                ExpressionAttributeValues={
                    ":xp": new_xp,
                    ":streak": new_streak,
                    ":last": datetime_to_iso(datetime.utcnow()),
                    ":updated": datetime_to_iso(datetime.utcnow())
                },
                ReturnValues="ALL_NEW"
            )
            return ProfilesDatabase._item_to_profile(response.get("Attributes", {}))
        except Exception:
            return None
    
    @staticmethod
    async def get_all_profile_ids() -> List[str]:
        """
        Get all profile IDs for background tasks.
        
        Returns:
            List of profile ID strings
        """
        table = ProfilesDatabase.get_table()
        
        profile_ids = []
        last_evaluated_key = None
        
        while True:
            if last_evaluated_key:
                response = table.scan(
                    ProjectionExpression="profileId",
                    ExclusiveStartKey=last_evaluated_key
                )
            else:
                response = table.scan(ProjectionExpression="profileId")
            
            for item in response.get("Items", []):
                profile_ids.append(item.get("profileId"))
            
            last_evaluated_key = response.get("LastEvaluatedKey")
            if not last_evaluated_key:
                break
        
        return profile_ids
    
    @staticmethod
    async def reset_streak(profile_id: str) -> Optional[ProfileInDB]:
        """
        Reset a profile's streak to 0.
        
        Args:
            profile_id: Profile's ID as string
            
        Returns:
            Updated ProfileInDB or None
        """
        if not profile_id:
            return None
        
        profile = await ProfilesDatabase.get_profile_by_id(profile_id)
        if not profile:
            return None
            
        table = ProfilesDatabase.get_table()
        
        try:
            response = table.update_item(
                Key={"userId": str(profile.master_user_id), "profileId": profile_id},
                UpdateExpression="SET gamification.current_streak_days = :streak, updated_at = :updated",
                ExpressionAttributeValues={
                    ":streak": 0,
                    ":updated": datetime_to_iso(datetime.utcnow())
                },
                ReturnValues="ALL_NEW"
            )
            return ProfilesDatabase._item_to_profile(response.get("Attributes", {}))
        except Exception:
            return None
    
    @staticmethod
    async def update_quiz_stats_v2(
        profile_id: str,
        xp_earned: int,
        is_today_quiz: bool,
        is_backlog: bool
    ) -> Optional[ProfileInDB]:
        """
        Update profile after quiz completion with proper streak logic.
        
        Args:
            profile_id: Profile's ID as string
            xp_earned: XP points earned from quiz
            is_today_quiz: Whether this is today's daily quiz
            is_backlog: Whether this is a backlog quiz
            
        Returns:
            Updated ProfileInDB or None
        """
        if not profile_id:
            return None
        
        profile = await ProfilesDatabase.get_profile_by_id(profile_id)
        if not profile:
            return None
            
        table = ProfilesDatabase.get_table()
        
        # Calculate new XP
        new_xp = profile.gamification.xp + xp_earned
        new_streak = profile.gamification.current_streak_days
        
        # Only update streak for today's quiz (not backlog)
        if is_today_quiz and not is_backlog:
            from datetime import timedelta
            
            last_activity = profile.gamification.last_activity_date
            today = date.today()
            
            if last_activity:
                last_date = last_activity.date() if isinstance(last_activity, datetime) else last_activity
                days_diff = (today - last_date).days
                
                if days_diff == 1:
                    new_streak += 1
                elif days_diff == 0:
                    if profile.gamification.current_streak_days == 0:
                        new_streak = 1
                else:
                    new_streak = 1
            else:
                new_streak = 1
        
        try:
            response = table.update_item(
                Key={"userId": str(profile.master_user_id), "profileId": profile_id},
                UpdateExpression="SET gamification.xp = :xp, gamification.current_streak_days = :streak, gamification.last_activity_date = :last, updated_at = :updated",
                ExpressionAttributeValues={
                    ":xp": new_xp,
                    ":streak": new_streak,
                    ":last": datetime_to_iso(datetime.utcnow()),
                    ":updated": datetime_to_iso(datetime.utcnow())
                },
                ReturnValues="ALL_NEW"
            )
            return ProfilesDatabase._item_to_profile(response.get("Attributes", {}))
        except Exception:
            return None
    
    @staticmethod
    async def update_learning_insights(
        profile_id: str,
        insights_data: Dict[str, Any]
    ) -> Optional[ProfileInDB]:
        """
        Update profile's learning insights.
        
        Args:
            profile_id: Profile's ID as string
            insights_data: Learning insights dictionary
            
        Returns:
            Updated ProfileInDB or None
        """
        if not profile_id:
            return None
        
        profile = await ProfilesDatabase.get_profile_by_id(profile_id)
        if not profile:
            return None
            
        table = ProfilesDatabase.get_table()
        
        insights_doc = {
            **insights_data,
            "generated_at": datetime_to_iso(datetime.utcnow())
        }
        
        try:
            response = table.update_item(
                Key={"userId": str(profile.master_user_id), "profileId": profile_id},
                UpdateExpression="SET learning_insights = :insights, updated_at = :updated",
                ExpressionAttributeValues={
                    ":insights": serialize_for_dynamo(insights_doc),
                    ":updated": datetime_to_iso(datetime.utcnow())
                },
                ReturnValues="ALL_NEW"
            )
            return ProfilesDatabase._item_to_profile(response.get("Attributes", {}))
        except Exception:
            return None
    
    @staticmethod
    async def get_learning_insights(profile_id: str) -> Optional[Dict[str, Any]]:
        """
        Get stored learning insights for a profile.
        
        Args:
            profile_id: Profile's ID as string
            
        Returns:
            Learning insights dictionary or None
        """
        if not profile_id:
            return None
        
        profile = await ProfilesDatabase.get_profile_by_id(profile_id)
        if not profile or not profile.learning_insights:
            return None
        
        return {
            "overall_assessment": profile.learning_insights.overall_assessment,
            "subject_insights": profile.learning_insights.subject_insights,
            "weak_topics_explanation": profile.learning_insights.weak_topics_explanation,
            "strengths": profile.learning_insights.strengths,
            "weekly_goals": profile.learning_insights.weekly_goals,
            "motivation_message": profile.learning_insights.motivation_message,
            "generated_at": datetime_to_iso(profile.learning_insights.generated_at)
        }
