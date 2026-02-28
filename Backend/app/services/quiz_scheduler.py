"""
Daily Quiz Generation - Lambda Handler for EventBridge
=======================================================
Generates daily quizzes for all profiles.
Triggered by EventBridge rule (cron: 0 0 * * ? *)

Setup:
------
1. Deploy as separate Lambda: digimasterji-quiz-scheduler
2. Create EventBridge rule:
   aws events put-rule --name digimasterji-daily-quiz \
     --schedule-expression "cron(0 0 * * ? *)" --state ENABLED
3. Add Lambda as target:
   aws events put-targets --rule digimasterji-daily-quiz \
     --targets "Id"="1","Arn"="arn:aws:lambda:us-east-1:ACCOUNT_ID:function:digimasterji-quiz-scheduler"
4. Grant permission:
   aws lambda add-permission --function-name digimasterji-quiz-scheduler \
     --statement-id eventbridge-invoke --action lambda:InvokeFunction \
     --principal events.amazonaws.com \
     --source-arn arn:aws:events:us-east-1:ACCOUNT_ID:rule/digimasterji-daily-quiz
"""

import logging
import asyncio
from datetime import date, datetime
from typing import Dict, Any

from app.database.profiles import ProfilesDatabase
from app.database.quizzes import QuizzesDatabase
from app.services.quiz_service import quiz_service

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Configuration
QUIZ_RETENTION_DAYS = 30  # Keep quizzes for 30 days


async def check_and_reset_streaks() -> int:
    """
    Check all profiles and reset streaks where quiz was not completed yesterday.
    Returns count of reset streaks.
    """
    logger.info("[QUIZ SCHEDULER] Checking streaks for all profiles")
    
    profile_ids = await ProfilesDatabase.get_all_profile_ids()
    reset_count = 0
    
    for profile_id in profile_ids:
        try:
            streak_broken = await QuizzesDatabase.check_streak_broken(profile_id)
            
            if streak_broken:
                profile = await ProfilesDatabase.get_profile_by_id(profile_id)
                if profile and profile.gamification.current_streak_days > 0:
                    await ProfilesDatabase.reset_streak(profile_id)
                    logger.info(f"[QUIZ SCHEDULER] Reset streak for profile {profile_id}")
                    reset_count += 1
                    
        except Exception as e:
            logger.error(f"[QUIZ SCHEDULER] Error checking streak for profile {profile_id}: {e}")
    
    logger.info(f"[QUIZ SCHEDULER] Streak check completed. Reset {reset_count} profiles.")
    return reset_count


async def cleanup_old_quizzes() -> int:
    """
    Delete quizzes older than QUIZ_RETENTION_DAYS (30 days).
    Returns count of deleted quizzes.
    """
    logger.info(f"[QUIZ SCHEDULER] Cleaning up quizzes older than {QUIZ_RETENTION_DAYS} days")
    
    deleted_count = await QuizzesDatabase.delete_old_quizzes(QUIZ_RETENTION_DAYS)
    
    logger.info(f"[QUIZ SCHEDULER] Deleted {deleted_count} old quizzes")
    return deleted_count


async def generate_daily_quizzes() -> Dict[str, int]:
    """
    Generate daily quizzes for all profiles.
    
    Returns:
        Dict with success_count, skip_count, error_count
    """
    logger.info("[QUIZ SCHEDULER] Starting daily quiz generation task")
    
    # First, check and reset streaks
    await check_and_reset_streaks()
    
    # Then, cleanup old quizzes
    await cleanup_old_quizzes()
    
    # Get all profile IDs
    profile_ids = await ProfilesDatabase.get_all_profile_ids()
    logger.info(f"[QUIZ SCHEDULER] Found {len(profile_ids)} profiles")
    
    success_count = 0
    skip_count = 0
    error_count = 0
    
    for profile_id in profile_ids:
        try:
            # Check if quiz already exists for today
            today = date.today()
            existing_quiz = await QuizzesDatabase.get_quiz_for_date(profile_id, today)
            
            if existing_quiz:
                logger.info(f"[QUIZ SCHEDULER] Quiz already exists for profile {profile_id}, skipping")
                skip_count += 1
                continue
            
            # Get profile data
            profile = await ProfilesDatabase.get_profile_by_id(profile_id)
            if not profile:
                logger.warning(f"[QUIZ SCHEDULER] Profile {profile_id} not found")
                error_count += 1
                continue
            
            profile_data = {
                "name": profile.name,
                "age": profile.age,
                "grade_level": profile.grade_level,
                "preferred_language": profile.preferred_language
            }
            
            # Generate quiz (5 questions)
            logger.info(f"[QUIZ SCHEDULER] Generating quiz for profile: {profile.name} ({profile_id})")
            
            quiz_create = await quiz_service.generate_quiz_from_history(
                profile_id=profile_id,
                profile_data=profile_data,
                num_questions=5
            )
            
            if quiz_create:
                quiz = await QuizzesDatabase.create_quiz(quiz_create)
                logger.info(f"[QUIZ SCHEDULER] Successfully created quiz {quiz.id} for profile {profile_id}")
                success_count += 1
            else:
                logger.error(f"[QUIZ SCHEDULER] Failed to generate quiz for profile {profile_id}")
                error_count += 1
                
        except Exception as e:
            logger.error(f"[QUIZ SCHEDULER] Error generating quiz for profile {profile_id}: {e}")
            error_count += 1
    
    logger.info(
        f"[QUIZ SCHEDULER] Daily quiz generation completed: "
        f"Success={success_count}, Skipped={skip_count}, Errors={error_count}"
    )
    
    return {
        "success_count": success_count,
        "skip_count": skip_count,
        "error_count": error_count,
        "total_profiles": len(profile_ids)
    }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for EventBridge scheduled invocation.
    
    EventBridge sends events like:
    {
        "version": "0",
        "id": "...",
        "detail-type": "Scheduled Event",
        "source": "aws.events",
        "time": "2026-02-28T00:00:00Z",
        "region": "us-east-1",
        "resources": ["arn:aws:events:..."],
        "detail": {}
    }
    """
    logger.info(f"[QUIZ SCHEDULER] Lambda invoked by EventBridge")
    logger.info(f"[QUIZ SCHEDULER] Event: {event}")
    
    try:
        # Run async quiz generation
        result = asyncio.get_event_loop().run_until_complete(generate_daily_quizzes())
        
        return {
            "statusCode": 200,
            "body": {
                "message": "Daily quiz generation completed",
                "timestamp": datetime.utcnow().isoformat(),
                "results": result
            }
        }
        
    except Exception as e:
        logger.error(f"[QUIZ SCHEDULER] Lambda execution failed: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "statusCode": 500,
            "body": {
                "message": "Daily quiz generation failed",
                "error": str(e)
            }
        }
