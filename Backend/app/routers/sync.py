"""
Sync Router - Data Synchronization
===================================
Endpoint for syncing user data on login.

This router provides the /sync/pull endpoint which fetches:
- All profiles for the logged-in master user
- All conversations for each profile
- Messages from the past N days (configurable via environment, no audio data)

DigiMasterJi - Multilingual AI Tutor for Rural Education
"""

import os
from fastapi import APIRouter, HTTPException, Depends, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from datetime import datetime

from app.models.sync import (
    SyncPullResponse,
    SyncProfileResponse,
    SyncConversationResponse,
    SyncMessageResponse,
    SyncGamificationResponse,
    SyncLearningPreferencesResponse,
    SyncQuizResponse,
    SyncQuizQuestionResponse
)
from app.database.users import UsersDatabase
from app.database.profiles import ProfilesDatabase
from app.database.conversations import ConversationsDatabase
from app.database.messages import MessagesDatabase
from app.database.quizzes import QuizzesDatabase
from app.utils.security import decode_access_token

# Sync configuration from environment
SYNC_DEFAULT_DAYS = int(os.getenv("SYNC_DEFAULT_DAYS", "180"))
SYNC_MAX_DAYS = int(os.getenv("SYNC_MAX_DAYS", "365"))

router = APIRouter(
    prefix="/sync",
    tags=["Sync"]
)

security = HTTPBearer()


async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Dependency to extract and validate user ID from JWT token.
    
    Args:
        credentials: HTTP Bearer token credentials
        
    Returns:
        User ID from token
        
    Raises:
        HTTPException: If token is invalid or user doesn't exist
    """
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    # Verify user exists
    user = await UsersDatabase.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user_id


@router.get(
    "/pull",
    response_model=SyncPullResponse,
    status_code=status.HTTP_200_OK,
    summary="Pull all user data for sync",
    description=f"""
    Fetch all user data on login for frontend synchronization.
    
    This endpoint returns a nested structure containing:
    - User information (master account)
    - All profiles under this account
    - All conversations for each profile
    - Messages from the past N days (configurable via `days` parameter, default: {SYNC_DEFAULT_DAYS}, max: {SYNC_MAX_DAYS})
    
    **Note:** Audio data is excluded from the response to reduce payload size.
    Audio fields (audio_url, audio_base64, etc.) are not included in messages.
    
    Use this endpoint when the user logs in to populate the frontend state.
    """
)
async def sync_pull(
    days: int = Query(
        default=SYNC_DEFAULT_DAYS,
        ge=1,
        le=SYNC_MAX_DAYS,
        description=f"Number of days to fetch messages for (default: {SYNC_DEFAULT_DAYS}, max: {SYNC_MAX_DAYS})"
    ),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Pull all data for the logged-in user.
    
    Returns nested structure:
    - User info
    - Profiles[]
      - Conversations[]
        - Messages[] (past N days, no audio)
    
    Args:
        days: Number of days to look back for messages (default from SYNC_DEFAULT_DAYS env var)
        current_user_id: Authenticated user's ID from JWT token
        
    Returns:
        SyncPullResponse with all user data
    """
    
    # Get user details
    user = await UsersDatabase.get_user_by_id(current_user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Initialize counters
    total_conversations = 0
    total_messages = 0
    total_quizzes = 0
    
    # Get all profiles for this user
    profiles_db = await ProfilesDatabase.get_profiles_by_user(current_user_id)
    
    profiles_response = []
    
    for profile in profiles_db:
        profile_id = str(profile.id)
        
        # Get all conversations for this profile
        conversations_db = await ConversationsDatabase.get_conversations_by_profile(
            profile_id,
            limit=100,  # Reasonable limit
            offset=0
        )
        
        conversations_response = []
        
        for conversation in conversations_db:
            conversation_id = str(conversation.id)
            
            # Get messages for this conversation (past N days, no audio)
            messages_data = await MessagesDatabase.get_messages_for_sync(
                conversation_id,
                days=days
            )
            
            # Convert to response models
            messages_response = [
                SyncMessageResponse(
                    _id=msg["_id"],
                    conversation_id=msg["conversation_id"],
                    profile_id=msg["profile_id"],
                    role=msg["role"],
                    content=msg["content"],
                    content_translated=msg["content_translated"],
                    timestamp=msg["timestamp"],
                    rag_references=msg["rag_references"]
                )
                for msg in messages_data
            ]
            
            total_messages += len(messages_response)
            
            # Build conversation response
            conv_response = SyncConversationResponse(
                _id=str(conversation.id),
                profile_id=str(conversation.profile_id),
                title=conversation.title,
                subject_tag=conversation.subject_tag,
                created_at=conversation.created_at,
                updated_at=conversation.updated_at,
                messages=messages_response
            )
            
            conversations_response.append(conv_response)
            total_conversations += 1
        
        # Build gamification response
        gamification_response = SyncGamificationResponse(
            xp=profile.gamification.xp if profile.gamification else 0,
            current_streak_days=profile.gamification.current_streak_days if profile.gamification else 0,
            last_activity_date=profile.gamification.last_activity_date if profile.gamification else None,
            badges=profile.gamification.badges if profile.gamification else []
        )
        
        # Build learning preferences response
        learning_prefs_response = SyncLearningPreferencesResponse(
            voice_enabled=profile.learning_preferences.voice_enabled if profile.learning_preferences else True
        )
        
        # Fetch quizzes for this profile (past N days)
        quizzes_db = await QuizzesDatabase.get_all_quizzes_for_profile(profile_id, days=days)
        quizzes_response = []
        
        for quiz in quizzes_db:
            # Convert questions to response model
            questions_response = [
                SyncQuizQuestionResponse(
                    question_id=q.question_id if hasattr(q, 'question_id') else q.get('question_id', ''),
                    question_text=q.question_text if hasattr(q, 'question_text') else q.get('question_text', ''),
                    options=q.options if hasattr(q, 'options') else q.get('options', []),
                    correct_answer=q.correct_answer if hasattr(q, 'correct_answer') else q.get('correct_answer', ''),
                    user_answer=q.user_answer if hasattr(q, 'user_answer') else q.get('user_answer')
                )
                for q in (quiz.questions if quiz.status == "completed" else [])
            ]
            
            quiz_response = SyncQuizResponse(
                _id=str(quiz.id),
                profile_id=str(quiz.profile_id),
                topic=quiz.topic,
                difficulty=quiz.difficulty,
                quiz_date=quiz.quiz_date,
                created_at=quiz.created_at,
                status=quiz.status,
                score=quiz.score,
                completed_at=quiz.completed_at,
                xp_earned=quiz.xp_earned,
                questions=questions_response,
                is_backlog=getattr(quiz, 'is_backlog', False) or (quiz.quiz_date < datetime.now().date())
            )
            quizzes_response.append(quiz_response)
        
        total_quizzes += len(quizzes_response)
        
        # Build profile response
        profile_response = SyncProfileResponse(
            _id=str(profile.id),
            master_user_id=str(profile.master_user_id),
            name=profile.name,
            age=profile.age,
            grade_level=profile.grade_level,
            preferred_language=profile.preferred_language,
            avatar=profile.avatar,
            gamification=gamification_response,
            learning_preferences=learning_prefs_response,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
            conversations=conversations_response,
            quizzes=quizzes_response
        )
        
        profiles_response.append(profile_response)
    
    # Build final response
    return SyncPullResponse(
        success=True,
        sync_timestamp=datetime.utcnow(),
        message="Data synced successfully",
        user_id=str(user.id),
        user_email=user.email,
        user_full_name=user.full_name,
        profiles=profiles_response,
        total_profiles=len(profiles_response),
        total_conversations=total_conversations,
        total_messages=total_messages,
        total_quizzes=total_quizzes,
        sync_period_days=days
    )
