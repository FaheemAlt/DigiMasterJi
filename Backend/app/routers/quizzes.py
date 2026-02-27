"""
Quizzes Router
==============
API endpoints for quiz generation, retrieval, and submission.
Handles daily streak and gamification logic.
"""

from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List
import logging
import asyncio
from datetime import date, datetime, timedelta

from app.models.quiz import (
    QuizResponse, QuizQuestionsResponse, QuizSubmission,
    QuizSubmissionResponse, QuizCreate, QuizRevisionResponse, QuizRevisionQuestion,
    QuizSummaryResponse, LearningInsightsResponse
)
from app.database.quizzes import QuizzesDatabase
from app.database.profiles import ProfilesDatabase
from app.services.quiz_service import quiz_service
from app.services.quiz_summary_service import quiz_summary_service
from app.utils.security import decode_access_token

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/quizzes",
    tags=["Quizzes"]
)

security = HTTPBearer()


async def get_current_profile_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Dependency to extract and validate profile ID from JWT token.
    """
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    token_type = payload.get("type")
    if token_type != "profile_token":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Profile token required for quiz operations"
        )
    
    profile_id = payload.get("sub")
    if not profile_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    # Verify profile exists
    profile = await ProfilesDatabase.get_profile_by_id(profile_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Profile not found"
        )
    
    return profile_id


@router.get("/pending", response_model=List[QuizResponse], status_code=status.HTTP_200_OK)
async def get_pending_quizzes(
    profile_id: str = Depends(get_current_profile_id)
):
    """
    Get all pending (not completed) quizzes for the current profile.
    
    Returns quizzes that are available to be taken.
    """
    try:
        logger.info(f"[QUIZ] Fetching pending quizzes for profile: {profile_id}")
        
        quizzes = await QuizzesDatabase.get_pending_quizzes_by_profile(profile_id)
        
        return [
            QuizResponse(
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
                total_questions=len(quiz.questions),
                is_backlog=getattr(quiz, 'is_backlog', False) or quiz.quiz_date < date.today()
            )
            for quiz in quizzes
        ]
        
    except Exception as e:
        logger.error(f"[QUIZ] Error fetching pending quizzes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch quizzes: {str(e)}"
        )


@router.get("/today", response_model=QuizResponse, status_code=status.HTTP_200_OK)
async def get_today_quiz(
    profile_id: str = Depends(get_current_profile_id)
):
    """
    Get today's quiz for the current profile.
    
    Returns the quiz for today's date if it exists.
    """
    try:
        logger.info(f"[QUIZ] Fetching today's quiz for profile: {profile_id}")
        
        today = date.today()
        quiz = await QuizzesDatabase.get_quiz_for_date(profile_id, today)
        
        if not quiz:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No quiz available for today. Check back tomorrow!"
            )
        
        return QuizResponse(
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
            total_questions=len(quiz.questions)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[QUIZ] Error fetching today's quiz: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch quiz: {str(e)}"
        )


@router.get("/{quiz_id}", response_model=QuizQuestionsResponse, status_code=status.HTTP_200_OK)
async def get_quiz_by_id(
    quiz_id: str,
    profile_id: str = Depends(get_current_profile_id)
):
    """
    Get quiz questions by ID (for taking the quiz).
    
    Returns questions WITHOUT correct answers to prevent cheating.
    """
    try:
        logger.info(f"[QUIZ] Fetching quiz: {quiz_id} for profile: {profile_id}")
        
        quiz = await QuizzesDatabase.get_quiz_by_id(quiz_id)
        
        if not quiz:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quiz not found"
            )
        
        # Verify quiz belongs to profile
        if str(quiz.profile_id) != profile_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this quiz"
            )
        
        # Remove correct answers from response (for pending quizzes)
        questions_without_answers = []
        for q in quiz.questions:
            q_dict = q.model_dump() if hasattr(q, 'model_dump') else q
            # Remove correct_answer field
            question_data = {
                "question_id": q_dict["question_id"],
                "question_text": q_dict["question_text"],
                "options": q_dict["options"]
            }
            questions_without_answers.append(question_data)
        
        return QuizQuestionsResponse(
            _id=str(quiz.id),
            profile_id=str(quiz.profile_id),
            topic=quiz.topic,
            difficulty=quiz.difficulty,
            quiz_date=quiz.quiz_date,
            questions=questions_without_answers,
            total_questions=len(quiz.questions)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[QUIZ] Error fetching quiz: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch quiz: {str(e)}"
        )


@router.post("/{quiz_id}/submit", response_model=QuizSubmissionResponse, status_code=status.HTTP_200_OK)
async def submit_quiz(
    quiz_id: str,
    submission: QuizSubmission,
    background_tasks: BackgroundTasks,
    profile_id: str = Depends(get_current_profile_id)
):
    """
    Submit quiz answers and get results.
    
    Calculates score, awards XP, and updates streak.
    Automatically triggers learning insights generation in background.
    """
    try:
        logger.info(f"[QUIZ] Submitting quiz: {quiz_id} for profile: {profile_id}")
        
        # Get quiz
        quiz = await QuizzesDatabase.get_quiz_by_id(quiz_id)
        
        if not quiz:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quiz not found"
            )
        
        # Verify quiz belongs to profile
        if str(quiz.profile_id) != profile_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this quiz"
            )
        
        # Check if already completed
        if quiz.status == "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quiz already completed"
            )
        
        # Calculate score
        correct_count = 0
        feedback = []
        
        for question in quiz.questions:
            q_dict = question.model_dump() if hasattr(question, 'model_dump') else question
            question_id = q_dict["question_id"]
            correct_answer = q_dict["correct_answer"]
            user_answer = submission.answers.get(question_id)
            
            is_correct = user_answer == correct_answer
            if is_correct:
                correct_count += 1
            
            feedback.append({
                "question_id": question_id,
                "question_text": q_dict["question_text"],
                "correct": is_correct,
                "user_answer": user_answer,
                "correct_answer": correct_answer
            })
        
        total_questions = len(quiz.questions)
        score = int((correct_count / total_questions) * 100)
        
        # Calculate XP (base 10 XP per correct answer)
        xp_earned = correct_count * 10
        
        # Bonus XP for perfect score
        if score == 100:
            xp_earned += 20
        
        # Update quiz in database
        updated_quiz = await QuizzesDatabase.update_quiz_completion(
            quiz_id=quiz_id,
            score=score,
            xp_earned=xp_earned,
            user_answers=submission.answers
        )
        
        if not updated_quiz:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update quiz"
            )
        
        # Check if this is a backlog quiz (quiz_date is before today)
        quiz_date = quiz.quiz_date
        completion_date = date.today()
        is_backlog = await QuizzesDatabase.is_backlog_quiz(quiz_id) or quiz_date < completion_date
        is_today_quiz = quiz_date == completion_date
        
        # Update profile stats with proper streak logic
        # Backlog quizzes give XP but don't affect streak
        updated_profile = await ProfilesDatabase.update_quiz_stats_v2(
            profile_id=profile_id,
            xp_earned=xp_earned,
            is_today_quiz=is_today_quiz,
            is_backlog=is_backlog
        )
        
        if not updated_profile:
            logger.warning(f"[QUIZ] Failed to update profile stats for {profile_id}")
            # Don't fail the request, quiz is still completed
        
        current_xp = updated_profile.gamification.xp if updated_profile else 0
        streak_days = updated_profile.gamification.current_streak_days if updated_profile else 0
        
        # Streak is only maintained for today's non-backlog quiz
        streak_maintained = is_today_quiz and not is_backlog
        
        logger.info(
            f"[QUIZ] Quiz submitted: score={score}%, xp={xp_earned}, "
            f"streak={streak_days} (is_backlog={is_backlog}, is_today={is_today_quiz})"
        )
        
        # Trigger background task to auto-generate and store learning insights
        # This runs asynchronously and doesn't block the response
        quiz_result = {
            "score": score,
            "correct_count": correct_count,
            "total_questions": total_questions,
            "xp_earned": xp_earned
        }
        
        async def generate_insights_async():
            """Background task wrapper for async insight generation."""
            try:
                await quiz_summary_service.auto_generate_and_store_insights(
                    profile_id=profile_id,
                    quiz_id=quiz_id,
                    quiz_result=quiz_result
                )
            except Exception as e:
                logger.error(f"[QUIZ] Background insights generation failed: {e}")
        
        # Schedule the background task - this runs after the response is sent
        background_tasks.add_task(generate_insights_async)
        logger.info(f"[QUIZ] Scheduled background insights generation for profile: {profile_id}")
        
        return QuizSubmissionResponse(
            quiz_id=quiz_id,
            score=score,
            correct_count=correct_count,
            total_questions=total_questions,
            xp_earned=xp_earned,
            current_xp=current_xp,
            streak_days=streak_days,
            streak_maintained=streak_maintained,
            is_backlog=is_backlog,
            feedback=feedback
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[QUIZ] Error submitting quiz: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit quiz: {str(e)}"
        )


# =============================================================================
# Quiz Summary & Learning Insights Endpoints
# =============================================================================

@router.post("/{quiz_id}/summary", response_model=QuizSummaryResponse, status_code=status.HTTP_200_OK)
async def generate_quiz_summary(
    quiz_id: str,
    profile_id: str = Depends(get_current_profile_id)
):
    """
    Generate an AI-powered summary immediately after completing a quiz.
    
    Returns personalized insights including:
    - Performance assessment
    - Topics to review
    - Concept explanations for wrong answers
    - Study tips
    - Encouraging message
    
    The summary takes into account both the current quiz and historical performance.
    """
    try:
        logger.info(f"[QUIZ SUMMARY] Generating summary for quiz: {quiz_id}, profile: {profile_id}")
        
        # Get the quiz
        quiz = await QuizzesDatabase.get_quiz_by_id(quiz_id)
        
        if not quiz:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quiz not found"
            )
        
        # Verify quiz belongs to profile
        if str(quiz.profile_id) != profile_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this quiz"
            )
        
        # Check if quiz is completed
        if quiz.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quiz must be completed to generate summary"
            )
        
        # Build quiz result data
        correct_count = 0
        for q in quiz.questions:
            q_dict = q.model_dump() if hasattr(q, 'model_dump') else q
            if q_dict.get("user_answer") == q_dict.get("correct_answer"):
                correct_count += 1
        
        quiz_result = {
            "score": quiz.score or 0,
            "correct_count": correct_count,
            "total_questions": len(quiz.questions),
            "xp_earned": quiz.xp_earned or 0
        }
        
        # Generate summary using AI
        summary = await quiz_summary_service.generate_quiz_summary(
            profile_id=profile_id,
            quiz_id=quiz_id,
            quiz_result=quiz_result
        )
        
        if not summary:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate quiz summary"
            )
        
        # Convert to response model
        from datetime import datetime
        
        return QuizSummaryResponse(
            quiz_id=summary.get("quiz_id", quiz_id),
            topic=summary.get("topic", quiz.topic),
            score=summary.get("score", quiz.score or 0),
            correct_count=summary.get("correct_count", correct_count),
            total_questions=summary.get("total_questions", len(quiz.questions)),
            performance_level=summary.get("performance_level", "good"),
            summary_text=summary.get("summary_text", ""),
            summary_text_hindi=summary.get("summary_text_hindi"),
            topics_to_review=summary.get("topics_to_review", []),
            encouragement=summary.get("encouragement", "Keep learning!"),
            encouragement_hindi=summary.get("encouragement_hindi"),
            study_tips=summary.get("study_tips", []),
            concepts_explained=[
                {"concept": c.get("concept", ""), "explanation": c.get("explanation", ""), "explanation_hindi": c.get("explanation_hindi")}
                for c in summary.get("concepts_explained", [])
            ],
            next_steps=summary.get("next_steps", ""),
            generated_at=datetime.fromisoformat(summary["generated_at"]) if summary.get("generated_at") else datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[QUIZ SUMMARY] Error generating summary: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate quiz summary: {str(e)}"
        )


@router.get("/insights/learning", response_model=LearningInsightsResponse, status_code=status.HTTP_200_OK)
async def get_learning_insights(
    days: int = 30,
    profile_id: str = Depends(get_current_profile_id)
):
    """
    Get comprehensive AI-powered learning insights for the student.
    
    This endpoint analyzes all quiz performance over the specified period
    and generates subject-wise insights including:
    - Overall assessment
    - Subject-wise analysis with recommendations
    - Weak topics with explanations
    - Strengths recognition
    - Weekly goals
    - Motivational message
    
    Args:
        days: Number of days to analyze (default: 30)
        
    Returns:
        LearningInsightsResponse with complete analytics
    """
    try:
        logger.info(f"[LEARNING INSIGHTS] Generating insights for profile: {profile_id}, days: {days}")
        
        # Generate insights
        insights = await quiz_summary_service.get_learning_insights(
            profile_id=profile_id,
            days=days
        )
        
        if not insights:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate learning insights"
            )
        
        # If no data, return appropriate message
        if not insights.get("has_data", True):
            return LearningInsightsResponse(
                has_data=False,
                message=insights.get("message"),
                message_hindi=insights.get("message_hindi")
            )
        
        # Build response model
        from datetime import datetime
        
        return LearningInsightsResponse(
            has_data=True,
            profile_name=insights.get("profile_name"),
            grade_level=insights.get("grade_level"),
            total_quizzes=insights.get("total_quizzes", 0),
            overall_average=insights.get("overall_average", 0),
            performance_trend=insights.get("performance_trend", "neutral"),
            analysis_period_days=insights.get("analysis_period_days", days),
            overall_assessment=insights.get("overall_assessment"),
            subject_insights=insights.get("subject_insights", []),
            weak_topics_explanation=insights.get("weak_topics_explanation", []),
            strengths=insights.get("strengths", []),
            weekly_goals=insights.get("weekly_goals", []),
            motivational_message=insights.get("motivational_message"),
            motivational_message_hindi=insights.get("motivational_message_hindi"),
            generated_at=datetime.fromisoformat(insights["generated_at"]) if insights.get("generated_at") else datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[LEARNING INSIGHTS] Error generating insights: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate learning insights: {str(e)}"
        )


@router.get("/insights/stored", status_code=status.HTTP_200_OK)
async def get_stored_insights(
    profile_id: str = Depends(get_current_profile_id)
):
    """
    Get stored learning insights from profile (auto-generated after quiz completion).
    
    This endpoint returns insights that were auto-generated in the background
    after quiz completion. No LLM call is made - just retrieves stored data.
    
    Returns:
        Stored insights or message indicating no insights available
    """
    try:
        logger.info(f"[STORED INSIGHTS] Fetching stored insights for profile: {profile_id}")
        
        # Get stored insights from profile
        stored_insights = await ProfilesDatabase.get_learning_insights(profile_id)
        
        if not stored_insights:
            return {
                "has_data": False,
                "message": "No learning insights available yet. Complete some quizzes to generate insights!",
                "message_hindi": "अभी तक कोई लर्निंग इनसाइट्स उपलब्ध नहीं है। इनसाइट्स जनरेट करने के लिए कुछ क्विज़ पूरे करें!"
            }
        
        return {
            "has_data": True,
            **stored_insights
        }
        
    except Exception as e:
        logger.error(f"[STORED INSIGHTS] Error fetching stored insights: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch stored insights: {str(e)}"
        )


@router.post("/insights/refresh", status_code=status.HTTP_200_OK)
async def refresh_insights(
    background_tasks: BackgroundTasks,
    profile_id: str = Depends(get_current_profile_id)
):
    """
    Manually trigger a refresh of learning insights.
    
    This regenerates insights based on latest quiz performance.
    The generation happens in background and returns immediately.
    
    Returns:
        Confirmation that refresh has been scheduled
    """
    try:
        logger.info(f"[INSIGHTS REFRESH] Manual refresh triggered for profile: {profile_id}")
        
        # Schedule background task
        async def refresh_async():
            """Background task wrapper for insight refresh."""
            try:
                # Use a dummy quiz result since we're regenerating from all data
                await quiz_summary_service.auto_generate_and_store_insights(
                    profile_id=profile_id,
                    quiz_id="manual_refresh",
                    quiz_result={}
                )
            except Exception as e:
                logger.error(f"[INSIGHTS REFRESH] Background refresh failed: {e}")
        
        # Schedule the background task - this runs after the response is sent
        background_tasks.add_task(refresh_async)
        
        return {
            "status": "scheduled",
            "message": "Learning insights refresh has been scheduled. Check back in a few moments.",
            "message_hindi": "लर्निंग इनसाइट्स रिफ्रेश शेड्यूल हो गया है। कुछ देर में वापस आकर चेक करें।"
        }
        
    except Exception as e:
        logger.error(f"[INSIGHTS REFRESH] Error scheduling refresh: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to schedule insights refresh: {str(e)}"
        )


@router.get("/streak/check", status_code=status.HTTP_200_OK)
async def check_streak_status(
    profile_id: str = Depends(get_current_profile_id)
):
    """
    Check current streak status and if today's quiz was completed.
    
    Returns streak info and whether user needs to complete today's quiz.
    """
    try:
        logger.info(f"[QUIZ] Checking streak status for profile: {profile_id}")
        
        # Get profile
        profile = await ProfilesDatabase.get_profile_by_id(profile_id)
        
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found"
            )
        
        # Check if today's quiz exists and its status
        today = date.today()
        today_quiz = await QuizzesDatabase.get_quiz_for_date(profile_id, today)
        
        quiz_available = today_quiz is not None
        quiz_completed = today_quiz.status == "completed" if today_quiz else False
        
        # Calculate streak status
        last_activity = profile.gamification.last_activity_date
        current_streak = profile.gamification.current_streak_days
        
        streak_at_risk = False
        if last_activity:
            last_date = last_activity.date() if isinstance(last_activity, datetime) else last_activity
            days_since_activity = (today - last_date).days
            
            # Streak at risk if no activity today and quiz not completed
            streak_at_risk = days_since_activity >= 1 and not quiz_completed
        
        return {
            "current_streak": current_streak,
            "total_xp": profile.gamification.xp,
            "quiz_available_today": quiz_available,
            "quiz_completed_today": quiz_completed,
            "streak_at_risk": streak_at_risk,
            "last_activity_date": last_activity.isoformat() if last_activity else None,
            "quiz_id": str(today_quiz.id) if today_quiz else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[QUIZ] Error checking streak status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check streak: {str(e)}"
        )


@router.post("/generate", response_model=QuizResponse, status_code=status.HTTP_201_CREATED)
async def generate_quiz_now(
    profile_id: str = Depends(get_current_profile_id)
):
    """
    Manually trigger quiz generation for the current profile.
    
    This is useful when the automatic generation failed or user wants a new quiz.
    Only generates if no quiz exists for today.
    """
    try:
        logger.info(f"[QUIZ] Manual quiz generation requested for profile: {profile_id}")
        
        # Check if quiz already exists for today
        today = date.today()
        existing_quiz = await QuizzesDatabase.get_quiz_for_date(profile_id, today)
        
        if existing_quiz:
            logger.info(f"[QUIZ] Quiz already exists for today, returning existing")
            return QuizResponse(
                _id=str(existing_quiz.id),
                profile_id=str(existing_quiz.profile_id),
                topic=existing_quiz.topic,
                difficulty=existing_quiz.difficulty,
                quiz_date=existing_quiz.quiz_date,
                created_at=existing_quiz.created_at,
                status=existing_quiz.status,
                score=existing_quiz.score,
                completed_at=existing_quiz.completed_at,
                xp_earned=existing_quiz.xp_earned,
                total_questions=len(existing_quiz.questions)
            )
        
        # Get profile data
        profile = await ProfilesDatabase.get_profile_by_id(profile_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found"
            )
        
        profile_data = {
            "name": profile.name,
            "age": profile.age,
            "grade_level": profile.grade_level,
            "preferred_language": profile.preferred_language
        }
        
        # Generate quiz
        quiz_create = await quiz_service.generate_quiz_from_history(
            profile_id=profile_id,
            profile_data=profile_data,
            num_questions=5
        )
        
        if not quiz_create:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate quiz. Please try again later."
            )
        
        # Save to database
        quiz = await QuizzesDatabase.create_quiz(quiz_create)
        
        logger.info(f"[QUIZ] Successfully generated quiz {quiz.id} for profile {profile_id}")
        
        return QuizResponse(
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
            total_questions=len(quiz.questions),
            is_backlog=False
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[QUIZ] Error generating quiz: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate quiz: {str(e)}"
        )


@router.get("/revision/all", response_model=List[QuizRevisionResponse], status_code=status.HTTP_200_OK)
async def get_quizzes_for_revision(
    days: int = 30,
    profile_id: str = Depends(get_current_profile_id)
):
    """
    Get all completed quizzes with full question details for revision.
    
    Returns quizzes from the last N days (default 30) with all questions,
    including correct answers and user's answers.
    """
    try:
        logger.info(f"[QUIZ] Fetching revision quizzes for profile: {profile_id}, days: {days}")
        
        quizzes = await QuizzesDatabase.get_quizzes_for_revision(profile_id, days)
        
        revision_responses = []
        for quiz in quizzes:
            # Build revision questions with correct/incorrect status
            revision_questions = []
            correct_count = 0
            
            for q in quiz.questions:
                q_dict = q.model_dump() if hasattr(q, 'model_dump') else q
                user_answer = q_dict.get("user_answer")
                correct_answer = q_dict.get("correct_answer")
                is_correct = user_answer == correct_answer
                
                if is_correct:
                    correct_count += 1
                
                revision_questions.append(QuizRevisionQuestion(
                    question_id=q_dict["question_id"],
                    question_text=q_dict["question_text"],
                    options=q_dict["options"],
                    correct_answer=correct_answer,
                    user_answer=user_answer,
                    is_correct=is_correct
                ))
            
            revision_responses.append(QuizRevisionResponse(
                _id=str(quiz.id),
                profile_id=str(quiz.profile_id),
                topic=quiz.topic,
                difficulty=quiz.difficulty,
                quiz_date=quiz.quiz_date,
                created_at=quiz.created_at,
                completed_at=quiz.completed_at,
                score=quiz.score or 0,
                xp_earned=quiz.xp_earned or 0,
                questions=revision_questions,
                total_questions=len(quiz.questions),
                correct_count=correct_count,
                is_backlog=getattr(quiz, 'is_backlog', False)
            ))
        
        return revision_responses
        
    except Exception as e:
        logger.error(f"[QUIZ] Error fetching revision quizzes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch revision quizzes: {str(e)}"
        )


@router.get("/backlog/dates", status_code=status.HTTP_200_OK)
async def get_backlog_dates(
    days: int = 30,
    profile_id: str = Depends(get_current_profile_id)
):
    """
    Get dates where quizzes were missed (no completed quiz).
    
    Returns list of dates within the last N days where user
    didn't complete a quiz. Only includes dates after profile creation.
    """
    try:
        logger.info(f"[QUIZ] Fetching missed quiz dates for profile: {profile_id}")
        
        # Get profile to check creation date
        profile = await ProfilesDatabase.get_profile_by_id(profile_id)
        profile_created_at = profile.created_at if profile else None
        
        missed_dates = await QuizzesDatabase.get_missed_quiz_dates(
            profile_id, 
            days, 
            profile_created_at=profile_created_at
        )
        
        return {
            "missed_dates": [d.isoformat() for d in missed_dates],
            "total_missed": len(missed_dates)
        }
        
    except Exception as e:
        logger.error(f"[QUIZ] Error fetching missed dates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch missed dates: {str(e)}"
        )


@router.post("/backlog/generate", response_model=QuizResponse, status_code=status.HTTP_201_CREATED)
async def generate_backlog_quiz(
    target_date: str,
    profile_id: str = Depends(get_current_profile_id)
):
    """
    Generate a backlog quiz for a missed date.
    
    Backlog quizzes award XP but do NOT affect streak.
    """
    try:
        # Parse target date
        try:
            quiz_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD"
            )
        
        # Validate date is in the past and within 30 days
        today = date.today()
        if quiz_date >= today:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Backlog date must be in the past"
            )
        
        days_ago = (today - quiz_date).days
        if days_ago > 30:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot generate backlog quiz for dates older than 30 days"
            )
        
        # Check if quiz already exists for this date
        existing_quiz = await QuizzesDatabase.get_quiz_for_date(profile_id, quiz_date)
        if existing_quiz:
            return QuizResponse(
                _id=str(existing_quiz.id),
                profile_id=str(existing_quiz.profile_id),
                topic=existing_quiz.topic,
                difficulty=existing_quiz.difficulty,
                quiz_date=existing_quiz.quiz_date,
                created_at=existing_quiz.created_at,
                status=existing_quiz.status,
                score=existing_quiz.score,
                completed_at=existing_quiz.completed_at,
                xp_earned=existing_quiz.xp_earned,
                total_questions=len(existing_quiz.questions),
                is_backlog=True
            )
        
        logger.info(f"[QUIZ] Generating backlog quiz for profile: {profile_id}, date: {quiz_date}")
        
        # Get profile data
        profile = await ProfilesDatabase.get_profile_by_id(profile_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found"
            )
        
        profile_data = {
            "name": profile.name,
            "age": profile.age,
            "grade_level": profile.grade_level,
            "preferred_language": profile.preferred_language
        }
        
        # Generate quiz
        quiz_create = await quiz_service.generate_quiz_from_history(
            profile_id=profile_id,
            profile_data=profile_data,
            num_questions=5
        )
        
        if not quiz_create:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate backlog quiz"
            )
        
        # Override the quiz_date to the backlog date
        quiz_create.quiz_date = quiz_date
        
        # Create as backlog quiz
        quiz = await QuizzesDatabase.create_backlog_quiz(quiz_create, is_backlog=True)
        
        logger.info(f"[QUIZ] Successfully generated backlog quiz {quiz.id}")
        
        return QuizResponse(
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
            total_questions=len(quiz.questions),
            is_backlog=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[QUIZ] Error generating backlog quiz: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate backlog quiz: {str(e)}"
        )


@router.delete("/cleanup/old", status_code=status.HTTP_200_OK)
async def cleanup_old_quizzes(
    days: int = 30,
    profile_id: str = Depends(get_current_profile_id)
):
    """
    Delete quizzes older than N days (default 30).
    
    This is also run automatically by the scheduler.
    """
    try:
        logger.info(f"[QUIZ] Cleaning up quizzes older than {days} days")
        
        deleted_count = await QuizzesDatabase.delete_old_quizzes(days)
        
        logger.info(f"[QUIZ] Deleted {deleted_count} old quizzes")
        
        return {
            "deleted_count": deleted_count,
            "retention_days": days
        }
        
    except Exception as e:
        logger.error(f"[QUIZ] Error cleaning up quizzes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup quizzes: {str(e)}"
        )


# ============================================
# Quiz Summary & Learning Insights Endpoints
# ============================================

@router.post("/{quiz_id}/summary", response_model=dict, status_code=status.HTTP_200_OK)
async def generate_quiz_summary(
    quiz_id: str,
    profile_id: str = Depends(get_current_profile_id)
):
    """
    Generate AI-powered summary for a completed quiz.
    
    Returns personalized insights based on:
    - Current quiz performance
    - Historical quiz results
    - Topics/concepts the student struggled with
    
    The response is in JSON format optimized for frontend rendering.
    """
    from app.services.quiz_summary_service import quiz_summary_service
    
    try:
        logger.info(f"[QUIZ SUMMARY] Generating summary for quiz: {quiz_id}, profile: {profile_id}")
        
        # Get the quiz
        quiz = await QuizzesDatabase.get_quiz_by_id(quiz_id)
        
        if not quiz:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quiz not found"
            )
        
        # Verify quiz belongs to profile
        if str(quiz.profile_id) != profile_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this quiz"
            )
        
        # Check if quiz is completed
        if quiz.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only generate summary for completed quizzes"
            )
        
        # Calculate quiz result from stored data
        correct_count = 0
        for question in quiz.questions:
            q_dict = question.model_dump() if hasattr(question, 'model_dump') else question
            if q_dict.get("user_answer") == q_dict.get("correct_answer"):
                correct_count += 1
        
        quiz_result = {
            "score": quiz.score or 0,
            "correct_count": correct_count,
            "total_questions": len(quiz.questions),
            "xp_earned": quiz.xp_earned or 0
        }
        
        # Generate summary with LLM
        summary = await quiz_summary_service.generate_quiz_summary(
            profile_id=profile_id,
            quiz_id=quiz_id,
            quiz_result=quiz_result
        )
        
        if not summary:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate quiz summary"
            )
        
        logger.info(f"[QUIZ SUMMARY] Successfully generated summary for quiz: {quiz_id}")
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[QUIZ SUMMARY] Error generating summary: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate quiz summary: {str(e)}"
        )


@router.get("/insights/learning", response_model=dict, status_code=status.HTTP_200_OK)
async def get_learning_insights(
    days: int = 30,
    profile_id: str = Depends(get_current_profile_id)
):
    """
    Get comprehensive AI-powered learning insights for the student.
    
    This endpoint provides:
    - Subject-wise performance analysis
    - Weak topics with explanations
    - Personalized study recommendations
    - Weekly learning goals
    - Motivational messages
    
    All insights are generated by the LLM in JSON format for easy
    frontend rendering. Includes both English and Hindi translations.
    
    Args:
        days: Number of days to analyze (default: 30)
    """
    from app.services.quiz_summary_service import quiz_summary_service
    
    try:
        logger.info(f"[LEARNING INSIGHTS] Generating insights for profile: {profile_id}, days: {days}")
        
        # Generate comprehensive insights
        insights = await quiz_summary_service.get_learning_insights(
            profile_id=profile_id,
            days=days
        )
        
        if not insights:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate learning insights"
            )
        
        logger.info(f"[LEARNING INSIGHTS] Successfully generated insights for profile: {profile_id}")
        return insights
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[LEARNING INSIGHTS] Error generating insights: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate learning insights: {str(e)}"
        )
