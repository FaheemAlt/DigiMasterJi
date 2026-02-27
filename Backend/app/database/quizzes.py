"""
Quizzes Database Operations - DynamoDB
=======================================
CRUD operations for the quizzes table.

DynamoDB Table: digimasterji-quizzes
- Partition Key: profileId (String)
- Sort Key: quizId (String)
- GSI: status-index (for fetching pending quizzes)

DigiMasterJi - AWS Migration
"""

from typing import Optional, List
from datetime import datetime, date, time, timedelta
from boto3.dynamodb.conditions import Key, Attr
import json

from app.models.quiz import QuizCreate, QuizInDB
from app.database.dynamo import (
    get_table,
    generate_id,
    TABLE_QUIZZES,
    datetime_to_iso,
    iso_to_datetime,
    serialize_for_dynamo,
    deserialize_from_dynamo
)


def date_to_iso(d: date) -> str:
    """Convert date to ISO string for DynamoDB storage."""
    if isinstance(d, datetime):
        return d.isoformat()
    return datetime.combine(d, time.min).isoformat()


def iso_to_date(iso_str: Optional[str]) -> Optional[date]:
    """Convert ISO string back to date."""
    if iso_str is None:
        return None
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.date()
    except (ValueError, TypeError):
        return None


class QuizzesDatabase:
    """Database operations for quizzes table."""
    
    TABLE_NAME = TABLE_QUIZZES
    
    @staticmethod
    def get_table():
        """Get quizzes table."""
        return get_table(QuizzesDatabase.TABLE_NAME)
    
    @staticmethod
    def _item_to_quiz(item: dict) -> QuizInDB:
        """Convert DynamoDB item to QuizInDB model."""
        item = deserialize_from_dynamo(item)
        
        # Parse questions from JSON string or list
        questions = item.get("questions", [])
        if isinstance(questions, str):
            questions = json.loads(questions)
        
        return QuizInDB(
            _id=item.get("quizId"),
            profile_id=item.get("profileId"),
            topic=item.get("topic"),
            source_conversation_ids=item.get("source_conversation_ids", []),
            questions=questions,
            difficulty=item.get("difficulty", "medium"),
            quiz_date=iso_to_date(item.get("quiz_date")),
            created_at=iso_to_datetime(item.get("created_at")),
            status=item.get("status", "pending"),
            score=item.get("score"),
            completed_at=iso_to_datetime(item.get("completed_at")),
            xp_earned=item.get("xp_earned"),
            is_backlog=item.get("is_backlog", False)
        )
    
    @staticmethod
    async def create_quiz(quiz_data: QuizCreate) -> QuizInDB:
        """
        Create a new quiz.
        
        Args:
            quiz_data: Quiz creation data
            
        Returns:
            QuizInDB: Created quiz document
        """
        if not quiz_data.profile_id:
            raise ValueError("Invalid profile_id")
            
        table = QuizzesDatabase.get_table()
        
        quiz_id = generate_id()
        now = datetime.utcnow()
        
        # Convert questions to JSON-serializable format
        questions = [q.model_dump() for q in quiz_data.questions]
        
        item = {
            "profileId": quiz_data.profile_id,
            "quizId": quiz_id,
            "topic": quiz_data.topic,
            "source_conversation_ids": quiz_data.source_conversation_ids,
            "questions": questions,
            "difficulty": quiz_data.difficulty,
            "quiz_date": date_to_iso(quiz_data.quiz_date),
            "created_at": datetime_to_iso(now),
            "status": "pending",
            "score": None,
            "completed_at": None,
            "xp_earned": None,
            "is_backlog": False
        }
        
        table.put_item(Item=serialize_for_dynamo(item))
        
        return QuizzesDatabase._item_to_quiz(item)
    
    @staticmethod
    async def get_quiz_by_id(quiz_id: str) -> Optional[QuizInDB]:
        """
        Get quiz by ID using GSI.
        
        Args:
            quiz_id: Quiz's ID as string
            
        Returns:
            QuizInDB or None
        """
        if not quiz_id:
            return None
            
        table = QuizzesDatabase.get_table()
        
        # Query using GSI on quizId
        response = table.query(
            IndexName="quizId-index",
            KeyConditionExpression=Key("quizId").eq(quiz_id)
        )
        
        items = response.get("Items", [])
        if items:
            return QuizzesDatabase._item_to_quiz(items[0])
        return None
    
    @staticmethod
    async def get_pending_quizzes_by_profile(profile_id: str) -> List[QuizInDB]:
        """
        Get all pending quizzes for a profile.
        
        Args:
            profile_id: Profile's ID as string
            
        Returns:
            List of pending QuizInDB
        """
        if not profile_id:
            return []
            
        table = QuizzesDatabase.get_table()
        
        response = table.query(
            KeyConditionExpression=Key("profileId").eq(profile_id),
            FilterExpression=Attr("status").eq("pending"),
            ScanIndexForward=False
        )
        
        quizzes = []
        for item in response.get("Items", []):
            quizzes.append(QuizzesDatabase._item_to_quiz(item))
        
        # Sort by created_at descending
        quizzes.sort(key=lambda x: x.created_at or datetime.min, reverse=True)
        
        return quizzes
    
    @staticmethod
    async def get_quiz_for_date(profile_id: str, quiz_date: date) -> Optional[QuizInDB]:
        """
        Get quiz for a specific date and profile.
        
        Args:
            profile_id: Profile's ID as string
            quiz_date: Date of the quiz
            
        Returns:
            QuizInDB or None
        """
        if not profile_id:
            return None
            
        table = QuizzesDatabase.get_table()
        
        quiz_date_iso = date_to_iso(quiz_date)
        
        response = table.query(
            KeyConditionExpression=Key("profileId").eq(profile_id),
            FilterExpression=Attr("quiz_date").eq(quiz_date_iso)
        )
        
        items = response.get("Items", [])
        if items:
            return QuizzesDatabase._item_to_quiz(items[0])
        return None
    
    @staticmethod
    async def update_quiz_completion(
        quiz_id: str,
        score: int,
        xp_earned: int,
        user_answers: dict
    ) -> Optional[QuizInDB]:
        """
        Mark quiz as completed with score and answers.
        
        Args:
            quiz_id: Quiz's ID as string
            score: Score percentage (0-100)
            xp_earned: XP points earned
            user_answers: Dictionary mapping question_id to user's answer
            
        Returns:
            Updated QuizInDB or None
        """
        if not quiz_id:
            return None
        
        quiz = await QuizzesDatabase.get_quiz_by_id(quiz_id)
        if not quiz:
            return None
            
        table = QuizzesDatabase.get_table()
        
        # Update questions with user answers
        updated_questions = []
        for question in quiz.questions:
            question_dict = question.model_dump() if hasattr(question, 'model_dump') else dict(question)
            question_id = question_dict.get("question_id")
            if question_id in user_answers:
                question_dict["user_answer"] = user_answers[question_id]
            updated_questions.append(question_dict)
        
        try:
            response = table.update_item(
                Key={"profileId": str(quiz.profile_id), "quizId": quiz_id},
                UpdateExpression="SET #status = :status, score = :score, xp_earned = :xp, completed_at = :completed, questions = :questions",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={
                    ":status": "completed",
                    ":score": score,
                    ":xp": xp_earned,
                    ":completed": datetime_to_iso(datetime.utcnow()),
                    ":questions": serialize_for_dynamo(updated_questions)
                },
                ReturnValues="ALL_NEW"
            )
            return QuizzesDatabase._item_to_quiz(response.get("Attributes", {}))
        except Exception:
            return None
    
    @staticmethod
    async def get_completed_quizzes_by_profile(
        profile_id: str,
        limit: Optional[int] = None,
        days: Optional[int] = None
    ) -> List[QuizInDB]:
        """
        Get completed quizzes for a profile.
        
        Args:
            profile_id: Profile's ID as string
            limit: Optional limit on number of quizzes
            days: Optional number of days to look back
            
        Returns:
            List of completed QuizInDB
        """
        if not profile_id:
            return []
            
        table = QuizzesDatabase.get_table()
        
        filter_expr = Attr("status").eq("completed")
        
        if days is not None:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            filter_expr = filter_expr & Attr("completed_at").gte(datetime_to_iso(cutoff_date))
        
        response = table.query(
            KeyConditionExpression=Key("profileId").eq(profile_id),
            FilterExpression=filter_expr,
            ScanIndexForward=False
        )
        
        quizzes = []
        for item in response.get("Items", []):
            quizzes.append(QuizzesDatabase._item_to_quiz(item))
        
        # Sort by completed_at descending
        quizzes.sort(key=lambda x: x.completed_at or datetime.min, reverse=True)
        
        if limit:
            quizzes = quizzes[:limit]
        
        return quizzes
    
    @staticmethod
    async def count_completed_quizzes(profile_id: str) -> int:
        """
        Count completed quizzes for a profile.
        
        Args:
            profile_id: Profile's ID as string
            
        Returns:
            Count of completed quizzes
        """
        if not profile_id:
            return 0
            
        table = QuizzesDatabase.get_table()
        
        response = table.query(
            KeyConditionExpression=Key("profileId").eq(profile_id),
            FilterExpression=Attr("status").eq("completed"),
            Select="COUNT"
        )
        
        return response.get("Count", 0)
    
    @staticmethod
    async def get_average_score(profile_id: str) -> float:
        """
        Calculate average quiz score for a profile.
        
        Args:
            profile_id: Profile's ID as string
            
        Returns:
            Average score (0-100)
        """
        if not profile_id:
            return 0.0
        
        quizzes = await QuizzesDatabase.get_completed_quizzes_by_profile(profile_id)
        
        if not quizzes:
            return 0.0
        
        scores = [q.score for q in quizzes if q.score is not None]
        if not scores:
            return 0.0
        
        return round(sum(scores) / len(scores), 2)
    
    @staticmethod
    async def get_quizzes_for_revision(
        profile_id: str,
        days: int = 30
    ) -> List[QuizInDB]:
        """
        Get completed quizzes for revision (last N days).
        
        Args:
            profile_id: Profile's ID as string
            days: Number of days to look back
            
        Returns:
            List of completed QuizInDB
        """
        return await QuizzesDatabase.get_completed_quizzes_by_profile(profile_id, days=days)
    
    @staticmethod
    async def get_all_quizzes_for_profile(
        profile_id: str,
        days: int = 30
    ) -> List[QuizInDB]:
        """
        Get all quizzes for a profile within N days.
        
        Args:
            profile_id: Profile's ID as string
            days: Number of days to look back
            
        Returns:
            List of QuizInDB
        """
        if not profile_id:
            return []
            
        table = QuizzesDatabase.get_table()
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        response = table.query(
            KeyConditionExpression=Key("profileId").eq(profile_id),
            FilterExpression=Attr("created_at").gte(datetime_to_iso(cutoff_date)),
            ScanIndexForward=False
        )
        
        quizzes = []
        for item in response.get("Items", []):
            quizzes.append(QuizzesDatabase._item_to_quiz(item))
        
        return quizzes
    
    @staticmethod
    async def delete_old_quizzes(days: int = 30) -> int:
        """
        Delete quizzes older than N days.
        
        Args:
            days: Number of days to retain quizzes
            
        Returns:
            Number of deleted quizzes
        """
        table = QuizzesDatabase.get_table()
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        cutoff_iso = datetime_to_iso(cutoff_date)
        
        # Scan for old quizzes
        response = table.scan(
            FilterExpression=Attr("created_at").lt(cutoff_iso),
            ProjectionExpression="profileId, quizId"
        )
        
        deleted_count = 0
        
        # Delete each quiz
        with table.batch_writer() as batch:
            for item in response.get("Items", []):
                batch.delete_item(
                    Key={
                        "profileId": item["profileId"],
                        "quizId": item["quizId"]
                    }
                )
                deleted_count += 1
        
        return deleted_count
    
    @staticmethod
    async def get_missed_quiz_dates(
        profile_id: str,
        days: int = 30,
        profile_created_at: datetime = None
    ) -> List[date]:
        """
        Get list of dates without completed quizzes.
        
        Args:
            profile_id: Profile's ID as string
            days: Number of days to check
            profile_created_at: Profile creation date
            
        Returns:
            List of dates without completed quizzes
        """
        if not profile_id:
            return []
        
        quizzes = await QuizzesDatabase.get_all_quizzes_for_profile(profile_id, days=days)
        
        # Build set of existing quiz dates and their status
        existing_quizzes = {}
        for quiz in quizzes:
            if quiz.quiz_date:
                existing_quizzes[quiz.quiz_date] = quiz.status
        
        # Find missed dates
        today = date.today()
        missed_dates = []
        
        if profile_created_at:
            profile_start_date = profile_created_at.date() if isinstance(profile_created_at, datetime) else profile_created_at
            earliest_check_date = profile_start_date + timedelta(days=1)
        else:
            earliest_check_date = today - timedelta(days=days)
        
        for i in range(1, days):
            check_date = today - timedelta(days=i)
            
            if check_date < earliest_check_date:
                continue
            
            if check_date not in existing_quizzes:
                missed_dates.append(check_date)
            elif existing_quizzes[check_date] == "pending":
                missed_dates.append(check_date)
        
        return missed_dates
    
    @staticmethod
    async def create_backlog_quiz(quiz_data: QuizCreate, is_backlog: bool = True) -> QuizInDB:
        """
        Create a backlog quiz.
        
        Args:
            quiz_data: Quiz creation data
            is_backlog: Whether this is a backlog quiz
            
        Returns:
            QuizInDB: Created quiz document
        """
        if not quiz_data.profile_id:
            raise ValueError("Invalid profile_id")
            
        table = QuizzesDatabase.get_table()
        
        quiz_id = generate_id()
        now = datetime.utcnow()
        
        questions = [q.model_dump() for q in quiz_data.questions]
        
        item = {
            "profileId": quiz_data.profile_id,
            "quizId": quiz_id,
            "topic": quiz_data.topic,
            "source_conversation_ids": quiz_data.source_conversation_ids,
            "questions": questions,
            "difficulty": quiz_data.difficulty,
            "quiz_date": date_to_iso(quiz_data.quiz_date),
            "created_at": datetime_to_iso(now),
            "status": "pending",
            "score": None,
            "completed_at": None,
            "xp_earned": None,
            "is_backlog": is_backlog
        }
        
        table.put_item(Item=serialize_for_dynamo(item))
        
        return QuizzesDatabase._item_to_quiz(item)
    
    @staticmethod
    async def is_backlog_quiz(quiz_id: str) -> bool:
        """
        Check if a quiz is a backlog quiz.
        
        Args:
            quiz_id: Quiz's ID as string
            
        Returns:
            True if backlog quiz
        """
        if not quiz_id:
            return False
        
        quiz = await QuizzesDatabase.get_quiz_by_id(quiz_id)
        if not quiz:
            return False
        
        if quiz.is_backlog:
            return True
        
        if quiz.quiz_date and quiz.quiz_date < date.today():
            return True
        
        return False
    
    @staticmethod
    async def check_streak_broken(profile_id: str) -> bool:
        """
        Check if streak should be reset.
        
        Args:
            profile_id: Profile's ID as string
            
        Returns:
            True if streak is broken
        """
        if not profile_id:
            return True
        
        yesterday = date.today() - timedelta(days=1)
        quiz = await QuizzesDatabase.get_quiz_for_date(profile_id, yesterday)
        
        if quiz and quiz.status == "completed":
            return False
        
        return True
