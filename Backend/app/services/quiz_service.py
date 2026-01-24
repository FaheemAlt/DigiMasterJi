"""
Quiz Service - AI-Powered Quiz Generation
==========================================
Generates personalized quizzes based on chat history using Ollama.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import date

from app.services.llm_service import LLMService
from app.database.messages import MessagesDatabase
from app.database.conversations import ConversationsDatabase
from app.models.quiz import QuizQuestion, QuizCreate

logger = logging.getLogger(__name__)


class QuizService:
    """Service for generating quizzes using AI."""
    
    def __init__(self):
        # Use longer timeout for quiz generation (complex JSON output)
        self.llm_service = LLMService(timeout=180.0)
    
    async def generate_quiz_from_history(
        self,
        profile_id: str,
        profile_data: Dict[str, Any],
        num_questions: int = 5
    ) -> Optional[QuizCreate]:
        """
        Generate a quiz based on recent chat history.
        
        Args:
            profile_id: Student profile ID
            profile_data: Profile information (name, age, grade, language)
            num_questions: Number of questions to generate (5-10)
            
        Returns:
            QuizCreate object or None if generation fails
        """
        try:
            logger.info(f"[QUIZ GEN] Generating quiz for profile: {profile_id}")
            
            # Get recent conversations (last 10)
            conversations = await ConversationsDatabase.get_conversations_by_profile(
                profile_id,
                limit=10,
                offset=0
            )
            
            if not conversations:
                logger.info(f"[QUIZ GEN] No conversation history found, generating general quiz")
                return await self.generate_general_quiz(profile_id, profile_data, num_questions)
            
            # Collect messages from recent conversations
            chat_context = []
            source_conversation_ids = []
            
            for conv in conversations[:5]:  # Use last 5 conversations
                conv_id = str(conv.id)
                source_conversation_ids.append(conv_id)
                
                messages = await MessagesDatabase.get_messages_by_conversation(conv_id)
                
                for msg in messages[-10:]:  # Last 10 messages per conversation
                    chat_context.append({
                        "role": msg.role,
                        "content": msg.content
                    })
            
            if not chat_context:
                logger.info(f"[QUIZ GEN] No messages found, generating general quiz")
                return await self.generate_general_quiz(profile_id, profile_data, num_questions)
            
            # Build context string
            context_str = "\\n".join([
                f"{msg['role'].upper()}: {msg['content']}"
                for msg in chat_context[-20:]  # Last 20 messages max
            ])
            
            # Determine topic from conversations
            topics = [conv.subject_tag for conv in conversations if conv.subject_tag]
            topic = topics[0] if topics else "General STEM"
            
            # Generate quiz using LLM
            quiz_data = await self._generate_quiz_with_llm(
                context_str,
                profile_data,
                topic,
                num_questions
            )
            
            if not quiz_data:
                logger.error(f"[QUIZ GEN] Failed to generate quiz from LLM")
                return None
            
            # Create QuizCreate object
            quiz_create = QuizCreate(
                profile_id=profile_id,
                topic=quiz_data.get("topic", topic),
                source_conversation_ids=source_conversation_ids,
                questions=quiz_data["questions"],
                difficulty=quiz_data.get("difficulty", "medium"),
                quiz_date=date.today()
            )
            
            logger.info(f"[QUIZ GEN] Successfully generated quiz: {quiz_create.topic}")
            return quiz_create
            
        except Exception as e:
            logger.error(f"[QUIZ GEN] Error generating quiz from history: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def generate_general_quiz(
        self,
        profile_id: str,
        profile_data: Dict[str, Any],
        num_questions: int = 5
    ) -> Optional[QuizCreate]:
        """
        Generate a general STEM quiz based on grade level.
        
        Args:
            profile_id: Student profile ID
            profile_data: Profile information (name, age, grade, language)
            num_questions: Number of questions to generate
            
        Returns:
            QuizCreate object or None if generation fails
        """
        try:
            logger.info(f"[QUIZ GEN] Generating general quiz for profile: {profile_id}")
            
            grade_level = profile_data.get("grade_level", "6th")
            language = profile_data.get("preferred_language", "English")
            
            # Generate quiz using LLM
            quiz_data = await self._generate_quiz_with_llm(
                context_str=None,
                profile_data=profile_data,
                topic=f"General STEM for {grade_level} grade",
                num_questions=num_questions
            )
            
            if not quiz_data:
                logger.error(f"[QUIZ GEN] Failed to generate general quiz from LLM")
                return None
            
            quiz_create = QuizCreate(
                profile_id=profile_id,
                topic=quiz_data.get("topic", f"General STEM - {grade_level}"),
                source_conversation_ids=[],
                questions=quiz_data["questions"],
                difficulty=quiz_data.get("difficulty", "medium"),
                quiz_date=date.today()
            )
            
            logger.info(f"[QUIZ GEN] Successfully generated general quiz: {quiz_create.topic}")
            return quiz_create
            
        except Exception as e:
            logger.error(f"[QUIZ GEN] Error generating general quiz: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def _generate_quiz_with_llm(
        self,
        context_str: Optional[str],
        profile_data: Dict[str, Any],
        topic: str,
        num_questions: int = 5
    ) -> Optional[Dict[str, Any]]:
        """
        Internal method to generate quiz using LLM with JSON output.
        
        Returns:
            Dictionary with quiz data or None
        """
        try:
            name = profile_data.get("name", "Student")
            grade_level = profile_data.get("grade_level", "6th")
            language = profile_data.get("preferred_language", "English")
            
            # Build the prompt
            if context_str:
                prompt = f"""You are DigiMasterJi, an AI tutor. Based on the following recent chat history with {name} (Grade {grade_level}), generate a quiz to test their understanding.

Chat History:
{context_str}

Generate a quiz with {num_questions} multiple-choice questions about the topics discussed. Questions should be in {language} language if the student used that language in the chat.

CRITICAL: You MUST respond with ONLY a valid JSON object. No markdown, no code blocks, no explanations - just pure JSON.

The JSON format must be exactly:
{{
  "topic": "Brief topic name",
  "difficulty": "medium",
  "questions": [
    {{
      "question_id": "q1",
      "question_text": "Your question here?",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer": "Option B"
    }}
  ]
}}

Requirements:
- Exactly {num_questions} questions
- Each question must have 4 options
- correct_answer must be exactly one of the options
- Questions should test understanding, not just memory
- Use {language} language if appropriate
- Make questions relevant to Grade {grade_level}

Generate the JSON now:"""
            else:
                prompt = f"""You are DigiMasterJi, an AI tutor. Generate a STEM quiz for {name} who is in Grade {grade_level}.

Create {num_questions} multiple-choice questions covering topics appropriate for {grade_level} grade (Science, Math, or Technology).

CRITICAL: You MUST respond with ONLY a valid JSON object. No markdown, no code blocks, no explanations - just pure JSON.

The JSON format must be exactly:
{{
  "topic": "Topic name for Grade {grade_level}",
  "difficulty": "medium",
  "questions": [
    {{
      "question_id": "q1",
      "question_text": "Your question in {language}?",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer": "Option B"
    }}
  ]
}}

Requirements:
- Exactly {num_questions} questions
- Each question must have 4 options
- correct_answer must be exactly one of the options
- Topics suitable for Grade {grade_level} STEM curriculum
- Questions in {language} language
- Mix of Science, Math, and basic Technology questions

Generate the JSON now:"""
            
            # Call LLM with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                logger.info(f"[QUIZ GEN] Calling LLM (attempt {attempt + 1}/{max_retries})")
                
                result = await self.llm_service.generate(
                    prompt=prompt,
                    temperature=0.7,
                    max_tokens=2048
                )
                
                if not result.get("success"):
                    logger.error(f"[QUIZ GEN] LLM call failed: {result.get('error')}")
                    continue
                
                response_text = result.get("response", "").strip()
                logger.info(f"[QUIZ GEN] Raw LLM response length: {len(response_text)} chars")
                
                # Try to extract JSON from response
                quiz_data = self._extract_json_from_response(response_text)
                
                if quiz_data and self._validate_quiz_data(quiz_data, num_questions):
                    logger.info(f"[QUIZ GEN] Successfully parsed and validated quiz")
                    return quiz_data
                
                logger.warning(f"[QUIZ GEN] Attempt {attempt + 1} failed validation, retrying...")
            
            logger.error(f"[QUIZ GEN] All {max_retries} attempts failed")
            return None
            
        except Exception as e:
            logger.error(f"[QUIZ GEN] Error in _generate_quiz_with_llm: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _extract_json_from_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from LLM response, handling markdown code blocks."""
        try:
            # Remove markdown code blocks if present
            text = response_text.strip()
            
            # Remove ```json or ``` markers
            if text.startswith("```"):
                lines = text.split("\\n")
                # Remove first line (```json) and last line (```)
                text = "\\n".join(lines[1:-1]) if len(lines) > 2 else text
                text = text.strip()
            
            # Try to find JSON object
            if "{" in text:
                start = text.find("{")
                # Find matching closing brace
                brace_count = 0
                end = start
                for i in range(start, len(text)):
                    if text[i] == "{":
                        brace_count += 1
                    elif text[i] == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            end = i + 1
                            break
                
                if end > start:
                    json_str = text[start:end]
                    return json.loads(json_str)
            
            # Try parsing entire text
            return json.loads(text)
            
        except json.JSONDecodeError as e:
            logger.error(f"[QUIZ GEN] JSON parse error: {e}")
            logger.error(f"[QUIZ GEN] Response text: {response_text[:500]}")
            return None
        except Exception as e:
            logger.error(f"[QUIZ GEN] Error extracting JSON: {e}")
            return None
    
    def _validate_quiz_data(self, quiz_data: Dict[str, Any], expected_questions: int) -> bool:
        """Validate quiz data structure."""
        try:
            # Check required fields
            if "questions" not in quiz_data:
                logger.error("[QUIZ GEN] Missing 'questions' field")
                return False
            
            questions = quiz_data["questions"]
            if not isinstance(questions, list):
                logger.error("[QUIZ GEN] 'questions' is not a list")
                return False
            
            if len(questions) != expected_questions:
                logger.warning(f"[QUIZ GEN] Expected {expected_questions} questions, got {len(questions)}")
                # Allow if close enough (within 2)
                if abs(len(questions) - expected_questions) > 2:
                    return False
            
            # Normalize difficulty field (LLM might return in other languages)
            difficulty = quiz_data.get("difficulty", "medium")
            difficulty_mapping = {
                # English
                "easy": "easy", "medium": "medium", "hard": "hard",
                # Hindi
                "आसान": "easy", "सरल": "easy", "मध्यम": "medium", "कठिन": "hard", "मुश्किल": "hard",
                # Gujarati
                "સરળ": "easy", "મધ્યમ": "medium", "કઠિન": "hard",
                # Marathi
                "सोपे": "easy", "मध्यम": "medium", "कठीण": "hard",
                # Tamil
                "எளிய": "easy", "நடுத்தர": "medium", "கடினம்": "hard",
                # Default
                "moderate": "medium", "simple": "easy", "difficult": "hard"
            }
            quiz_data["difficulty"] = difficulty_mapping.get(difficulty.lower().strip(), "medium")
            
            # Validate each question
            for i, q in enumerate(questions):
                if not isinstance(q, dict):
                    logger.error(f"[QUIZ GEN] Question {i} is not a dict")
                    return False
                
                required_fields = ["question_id", "question_text", "options", "correct_answer"]
                for field in required_fields:
                    if field not in q:
                        logger.error(f"[QUIZ GEN] Question {i} missing field: {field}")
                        return False
                
                # Validate options
                if not isinstance(q["options"], list) or len(q["options"]) < 2:
                    logger.error(f"[QUIZ GEN] Question {i} has invalid options")
                    return False
                
                # Validate correct_answer is in options
                if q["correct_answer"] not in q["options"]:
                    logger.error(f"[QUIZ GEN] Question {i} correct_answer not in options")
                    return False
                
                # Add user_answer field if not present
                if "user_answer" not in q:
                    q["user_answer"] = None
            
            # Convert to QuizQuestion objects
            try:
                quiz_data["questions"] = [QuizQuestion(**q) for q in questions]
            except Exception as e:
                logger.error(f"[QUIZ GEN] Error creating QuizQuestion objects: {e}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"[QUIZ GEN] Error validating quiz data: {e}")
            return False


# Global instance
quiz_service = QuizService()
