"""
Quiz Summary Service - AI-Powered Learning Analytics
=====================================================
Generates personalized learning summaries based on quiz performance.
Identifies weak topics and provides subject-wise recommendations.
Includes RAG integration for contextual educational content.

DigiMasterJi - Multilingual AI Tutor for Rural Education
"""

import json
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from app.services.llm_service import LLMService
from app.database.quizzes import QuizzesDatabase
from app.database.profiles import ProfilesDatabase
from app.database.knowledge_base import vector_search

logger = logging.getLogger(__name__)


class QuizSummaryService:
    """Service for generating AI-powered quiz summaries and learning insights."""
    
    def __init__(self):
        self.llm_service = LLMService(timeout=180.0)
    
    async def auto_generate_and_store_insights(
        self,
        profile_id: str,
        quiz_id: str,
        quiz_result: Dict[str, Any]
    ) -> bool:
        """
        Automatically generate and store learning insights after quiz completion.
        This runs as a background task after quiz submission.
        
        Args:
            profile_id: Student profile ID
            quiz_id: The completed quiz ID
            quiz_result: Quiz submission results
            
        Returns:
            True if insights were generated and stored successfully
        """
        try:
            logger.info(f"[AUTO INSIGHTS] Starting background insight generation for profile: {profile_id}")
            
            # Get profile data
            profile = await ProfilesDatabase.get_profile_by_id(profile_id)
            if not profile:
                logger.error(f"[AUTO INSIGHTS] Profile not found: {profile_id}")
                return False
            
            profile_data = {
                "name": profile.name,
                "age": profile.age,
                "grade_level": profile.grade_level,
                "preferred_language": profile.preferred_language
            }
            
            # Get all completed quizzes for comprehensive analysis
            completed_quizzes = await QuizzesDatabase.get_completed_quizzes_by_profile(
                profile_id=profile_id,
                days=30
            )
            
            if not completed_quizzes:
                logger.info(f"[AUTO INSIGHTS] No quizzes to analyze for profile: {profile_id}")
                return False
            
            # Analyze quiz history
            history_analysis = self._analyze_quiz_history(completed_quizzes)
            
            # Get RAG context for weak topics to enhance insights
            rag_context = await self._get_rag_context_for_insights(history_analysis)
            
            # Generate comprehensive insights with RAG context
            insights = await self._generate_insights_with_llm_and_rag(
                profile_data=profile_data,
                history_analysis=history_analysis,
                quizzes=completed_quizzes,
                rag_context=rag_context
            )
            
            if not insights:
                logger.error(f"[AUTO INSIGHTS] Failed to generate insights for profile: {profile_id}")
                return False
            
            # Store insights directly - keep the LLM format that frontend expects
            # Only add metadata fields, don't transform the structure
            storage_data = {
                **insights,
                "generated_at": datetime.utcnow().isoformat(),
                "analysis_period_days": 30
            }
            
            # Store insights in profile
            result = await ProfilesDatabase.update_learning_insights(
                profile_id=profile_id,
                insights_data=storage_data
            )
            
            if result:
                logger.info(f"[AUTO INSIGHTS] Successfully stored insights for profile: {profile_id}")
                return True
            else:
                logger.error(f"[AUTO INSIGHTS] Failed to store insights for profile: {profile_id}")
                return False
                
        except Exception as e:
            logger.error(f"[AUTO INSIGHTS] Error in auto-generation: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def _get_rag_context_for_insights(
        self,
        history_analysis: Dict[str, Any]
    ) -> str:
        """
        Get relevant educational content from RAG for weak topics.
        
        Args:
            history_analysis: Analysis of quiz history
            
        Returns:
            RAG context string for LLM prompt
        """
        try:
            weak_topics = []
            
            # Extract weak areas from subject stats
            for subject, stats in history_analysis.get("subject_stats", {}).items():
                if stats.get("average_score", 100) < 70:
                    topics = stats.get("topics", [])
                    weak_topics.extend(topics[:3])  # Get top 3 weak topics per subject
            
            # Also add topics from weak questions
            weak_questions = history_analysis.get("weak_questions", [])
            for wq in weak_questions[:5]:
                weak_topics.append(wq.get("topic", ""))
            
            if not weak_topics:
                return ""
            
            # Create a search query from weak topics
            search_query = " ".join(set(weak_topics[:10]))
            
            # Search knowledge base using Bedrock (handles embedding internally)
            rag_results = await vector_search(
                query_text=search_query,
                limit=5,
                subject=None,
                language=None
            )
            
            # Build RAG context string
            if not rag_results:
                return ""
            
            context_parts = []
            context_parts.append("=== Relevant Educational Content for Weak Topics ===")
            
            for i, chunk in enumerate(rag_results, 1):
                title = chunk.get("title", "Untitled")
                content = chunk.get("content_chunk", "")[:500]  # Limit content
                subject = chunk.get("subject", "General")
                
                context_parts.append(f"\n[Resource {i}: {subject} - {title}]")
                context_parts.append(content)
            
            context_parts.append("\n=== End of Educational Content ===")
            
            logger.info(f"[AUTO INSIGHTS] Retrieved {len(rag_results)} RAG chunks for insights")
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"[AUTO INSIGHTS] Error getting RAG context: {e}")
            return ""
    
    async def _generate_insights_with_llm_and_rag(
        self,
        profile_data: Dict[str, Any],
        history_analysis: Dict[str, Any],
        quizzes: List,
        rag_context: str
    ) -> Optional[Dict[str, Any]]:
        """Generate comprehensive learning insights using LLM with RAG context."""
        
        language = profile_data.get("preferred_language", "English")
        grade = profile_data.get("grade_level", "6th")
        name = profile_data.get("name", "Student")
        
        # Build subject breakdown
        subject_breakdown = []
        for subject, stats in history_analysis.get("subject_stats", {}).items():
            subject_breakdown.append({
                "subject": subject,
                "quizzes_taken": stats["total_quizzes"],
                "average_score": round(stats.get("average_score", 0), 1),
                "topics_covered": stats.get("topics", [])[:5],
                "weak_questions_count": len(stats.get("weak_questions", []))
            })
        
        # Get sample weak questions
        weak_questions_sample = history_analysis.get("weak_questions", [])[:10]
        
        prompt = f"""You are DigiMasterJi, an educational AI assistant. Generate comprehensive learning insights for a student.

Student Profile:
- Name: {name}
- Grade: {grade}
- Preferred Language: {language}

Performance Overview:
- Total Quizzes: {history_analysis.get('total_quizzes', 0)}
- Overall Average: {history_analysis.get('overall_average', 0)}%
- Performance Trend: {history_analysis.get('recent_trend', 'neutral')}
- Strong Topics: {', '.join(history_analysis.get('strong_topics', [])) or 'None identified yet'}

Subject-wise Breakdown:
{json.dumps(subject_breakdown, indent=2)}

Sample Questions Student Got Wrong:
{json.dumps(weak_questions_sample, indent=2)}

{rag_context if rag_context else ""}

Based on the above data and the educational content provided, generate a JSON response with this EXACT structure (no markdown, pure JSON):
{{
    "overall_assessment": {{
        "level": "excellent|good|average|needs_improvement",
        "summary": "2-3 sentence overall assessment",
        "summary_hindi": "Same in Hindi"
    }},
    "subject_insights": [
        {{
            "subject": "Subject name",
            "status": "strong|average|weak",
            "score_average": 0,
            "performance_trend": "improving|stable|declining",
            "improvement_areas": ["List of specific topics/concepts to improve"],
            "strong_areas": ["List of topics the student is good at"],
            "recommendation": "Specific recommendation for this subject",
            "recommendation_hindi": "Same in Hindi"
        }}
    ],
    "weak_topics_explanation": [
        {{
            "topic": "Topic name",
            "subject": "Subject",
            "why_important": "Why this topic matters",
            "simple_explanation": "Brief, grade-appropriate explanation using curriculum content",
            "simple_explanation_hindi": "Same in Hindi",
            "practice_tip": "How to practice this topic"
        }}
    ],
    "strengths": [
        {{
            "area": "Area of strength",
            "praise": "Encouraging message about this strength",
            "praise_hindi": "Same in Hindi"
        }}
    ],
    "weekly_goals": [
        {{
            "goal": "Specific, achievable goal",
            "goal_hindi": "Same in Hindi",
            "subject": "Related subject"
        }}
    ],
    "personalized_recommendations": ["List of 3-5 specific action items for the student"],
    "motivational_message": "An encouraging message based on their progress",
    "motivational_message_hindi": "Same in Hindi"
}}

Important:
- Use the educational content provided to give accurate, curriculum-aligned recommendations
- Be specific based on the actual performance data
- Keep all explanations suitable for {grade} grade students
- Provide actionable, practical recommendations
- Be encouraging while honest about areas needing improvement
- Return ONLY valid JSON, no other text"""

        try:
            result = await self.llm_service.generate(
                prompt=prompt,
                temperature=0.7,
                max_tokens=3000
            )
            
            if not result.get("success"):
                logger.error(f"[AUTO INSIGHTS] LLM generation failed: {result.get('error')}")
                return self._get_fallback_insights(history_analysis)
            
            response_text = result.get("response", "")
            
            # Parse JSON from response
            insights = self._parse_json_response(response_text)
            if insights:
                insights["has_data"] = True
                insights["profile_name"] = name
                insights["grade_level"] = grade
                insights["total_quizzes"] = history_analysis.get("total_quizzes", 0)
                insights["overall_average"] = history_analysis.get("overall_average", 0)
                insights["performance_trend"] = history_analysis.get("recent_trend", "neutral")
                insights["generated_at"] = datetime.utcnow().isoformat()
                insights["analysis_period_days"] = 30
                insights["rag_enhanced"] = bool(rag_context)
                return insights
            
            return self._get_fallback_insights(history_analysis)
            
        except Exception as e:
            logger.error(f"[AUTO INSIGHTS] Error in LLM generation: {e}")
            return self._get_fallback_insights(history_analysis)
    
    def _transform_insights_for_storage(self, insights: Dict[str, Any]) -> Dict[str, Any]:
        """Transform LLM insights to storage format for ProfilesDatabase."""
        
        # Extract subject data
        subjects = []
        for si in insights.get("subject_insights", []):
            subjects.append({
                "subject": si.get("subject", ""),
                "average_score": si.get("score_average", 0),
                "total_quizzes": 0,  # Will be updated from stats
                "performance_trend": si.get("performance_trend", "stable"),
                "weak_topics": si.get("improvement_areas", []),
                "strong_topics": si.get("strong_areas", []),
                "recommendation": si.get("recommendation", "")
            })
        
        # Build storage format
        return {
            "overall_score": insights.get("overall_average", 0),
            "total_quizzes_analyzed": insights.get("total_quizzes", 0),
            "subjects": subjects,
            "weak_areas_summary": insights.get("overall_assessment", {}).get("summary", ""),
            "strengths_summary": ", ".join([s.get("area", "") for s in insights.get("strengths", [])]),
            "personalized_recommendations": insights.get("personalized_recommendations", []),
            "weekly_goals": [g.get("goal", "") for g in insights.get("weekly_goals", [])],
            "motivational_message": insights.get("motivational_message", ""),
            "motivational_message_hindi": insights.get("motivational_message_hindi", "")
        }
    
    async def generate_quiz_summary(
        self,
        profile_id: str,
        quiz_id: str,
        quiz_result: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a summary immediately after a quiz is completed.
        
        Args:
            profile_id: Student profile ID
            quiz_id: The completed quiz ID
            quiz_result: Quiz submission results (score, feedback, etc.)
            
        Returns:
            Dictionary with summary in JSON format for frontend rendering
        """
        try:
            logger.info(f"[QUIZ SUMMARY] Generating summary for quiz: {quiz_id}")
            
            # Get the completed quiz
            quiz = await QuizzesDatabase.get_quiz_by_id(quiz_id)
            if not quiz:
                logger.error(f"[QUIZ SUMMARY] Quiz not found: {quiz_id}")
                return None
            
            # Get profile data
            profile = await ProfilesDatabase.get_profile_by_id(profile_id)
            if not profile:
                logger.error(f"[QUIZ SUMMARY] Profile not found: {profile_id}")
                return None
            
            profile_data = {
                "name": profile.name,
                "age": profile.age,
                "grade_level": profile.grade_level,
                "preferred_language": profile.preferred_language
            }
            
            # Get recent quiz history for context (last 30 days)
            recent_quizzes = await QuizzesDatabase.get_completed_quizzes_by_profile(
                profile_id=profile_id,
                days=30
            )
            
            # Analyze quiz history
            history_analysis = self._analyze_quiz_history(recent_quizzes)
            
            # Build the prompt for LLM
            summary = await self._generate_summary_with_llm(
                quiz=quiz,
                quiz_result=quiz_result,
                profile_data=profile_data,
                history_analysis=history_analysis
            )
            
            return summary
            
        except Exception as e:
            logger.error(f"[QUIZ SUMMARY] Error generating summary: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def get_learning_insights(
        self,
        profile_id: str,
        days: int = 30
    ) -> Optional[Dict[str, Any]]:
        """
        Generate comprehensive learning insights for the student profile.
        This is for the dedicated Learning Insights page.
        
        Args:
            profile_id: Student profile ID
            days: Number of days to analyze (default 30)
            
        Returns:
            Dictionary with subject-wise insights, weak topics, recommendations
        """
        try:
            logger.info(f"[LEARNING INSIGHTS] Generating insights for profile: {profile_id}")
            
            # Get profile data
            profile = await ProfilesDatabase.get_profile_by_id(profile_id)
            if not profile:
                logger.error(f"[LEARNING INSIGHTS] Profile not found: {profile_id}")
                return None
            
            profile_data = {
                "name": profile.name,
                "age": profile.age,
                "grade_level": profile.grade_level,
                "preferred_language": profile.preferred_language
            }
            
            # Get all completed quizzes
            completed_quizzes = await QuizzesDatabase.get_completed_quizzes_by_profile(
                profile_id=profile_id,
                days=days
            )
            
            if not completed_quizzes:
                return {
                    "has_data": False,
                    "message": "No quiz data available yet. Complete some quizzes to see your learning insights!",
                    "message_hi": "अभी तक कोई क्विज़ डेटा उपलब्ध नहीं है। अपनी लर्निंग इनसाइट्स देखने के लिए कुछ क्विज़ पूरे करें!"
                }
            
            # Analyze quiz history
            history_analysis = self._analyze_quiz_history(completed_quizzes)
            
            # Generate insights with LLM
            insights = await self._generate_insights_with_llm(
                profile_data=profile_data,
                history_analysis=history_analysis,
                quizzes=completed_quizzes
            )
            
            return insights
            
        except Exception as e:
            logger.error(f"[LEARNING INSIGHTS] Error generating insights: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _analyze_quiz_history(self, quizzes: List) -> Dict[str, Any]:
        """
        Analyze quiz history to extract statistics and patterns.
        
        Args:
            quizzes: List of QuizInDB objects
            
        Returns:
            Dictionary with analysis results
        """
        if not quizzes:
            return {
                "total_quizzes": 0,
                "subject_stats": {},
                "overall_average": 0,
                "recent_trend": "neutral",
                "weak_questions": [],
                "strong_topics": []
            }
        
        # Subject-wise statistics
        subject_stats = {}
        weak_questions = []
        all_scores = []
        
        for quiz in quizzes:
            topic = quiz.topic
            score = quiz.score or 0
            all_scores.append(score)
            
            # Extract subject from topic (simple heuristic)
            subject = self._extract_subject(topic)
            
            if subject not in subject_stats:
                subject_stats[subject] = {
                    "total_quizzes": 0,
                    "total_score": 0,
                    "topics": [],
                    "weak_questions": []
                }
            
            subject_stats[subject]["total_quizzes"] += 1
            subject_stats[subject]["total_score"] += score
            subject_stats[subject]["topics"].append(topic)
            
            # Analyze questions
            for question in quiz.questions:
                q_dict = question.model_dump() if hasattr(question, 'model_dump') else question
                user_answer = q_dict.get("user_answer")
                correct_answer = q_dict.get("correct_answer")
                
                if user_answer and user_answer != correct_answer:
                    weak_questions.append({
                        "topic": topic,
                        "subject": subject,
                        "question": q_dict.get("question_text", ""),
                        "user_answer": user_answer,
                        "correct_answer": correct_answer
                    })
                    subject_stats[subject]["weak_questions"].append(q_dict.get("question_text", ""))
        
        # Calculate averages
        for subject in subject_stats:
            total = subject_stats[subject]["total_quizzes"]
            if total > 0:
                subject_stats[subject]["average_score"] = subject_stats[subject]["total_score"] / total
            else:
                subject_stats[subject]["average_score"] = 0
        
        # Calculate overall average
        overall_average = sum(all_scores) / len(all_scores) if all_scores else 0
        
        # Calculate trend (compare recent 5 with earlier)
        recent_scores = all_scores[:5]
        earlier_scores = all_scores[5:10] if len(all_scores) > 5 else []
        
        trend = "neutral"
        if recent_scores and earlier_scores:
            recent_avg = sum(recent_scores) / len(recent_scores)
            earlier_avg = sum(earlier_scores) / len(earlier_scores)
            if recent_avg > earlier_avg + 5:
                trend = "improving"
            elif recent_avg < earlier_avg - 5:
                trend = "declining"
        
        # Identify strong topics (subjects with avg >= 80)
        strong_topics = [s for s, stats in subject_stats.items() if stats["average_score"] >= 80]
        
        return {
            "total_quizzes": len(quizzes),
            "subject_stats": subject_stats,
            "overall_average": round(overall_average, 1),
            "recent_trend": trend,
            "weak_questions": weak_questions[:20],  # Limit to 20 most recent
            "strong_topics": strong_topics
        }
    
    def _extract_subject(self, topic: str) -> str:
        """Extract subject category from topic string."""
        topic_lower = topic.lower()
        
        # Science subjects
        if any(kw in topic_lower for kw in ["physics", "force", "motion", "energy", "light", "sound", "electricity", "magnet"]):
            return "Physics"
        if any(kw in topic_lower for kw in ["chemistry", "atom", "molecule", "element", "compound", "reaction", "acid", "base"]):
            return "Chemistry"
        if any(kw in topic_lower for kw in ["biology", "cell", "plant", "animal", "human body", "photosynthesis", "digestion", "respiration"]):
            return "Biology"
        
        # Math subjects
        if any(kw in topic_lower for kw in ["math", "algebra", "geometry", "arithmetic", "fraction", "decimal", "percent", "equation", "number"]):
            return "Mathematics"
        
        # Other subjects
        if any(kw in topic_lower for kw in ["history", "geography", "civics", "economics", "social"]):
            return "Social Science"
        
        if any(kw in topic_lower for kw in ["english", "hindi", "language", "grammar"]):
            return "Language"
        
        return "General STEM"
    
    async def _generate_summary_with_llm(
        self,
        quiz,
        quiz_result: Dict[str, Any],
        profile_data: Dict[str, Any],
        history_analysis: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Generate quiz summary using LLM."""
        
        # Build questions analysis
        questions_analysis = []
        for q in quiz.questions:
            q_dict = q.model_dump() if hasattr(q, 'model_dump') else q
            user_answer = q_dict.get("user_answer")
            correct_answer = q_dict.get("correct_answer")
            is_correct = user_answer == correct_answer
            questions_analysis.append({
                "question": q_dict.get("question_text", ""),
                "user_answer": user_answer,
                "correct_answer": correct_answer,
                "is_correct": is_correct
            })
        
        # Get wrong answers for focus
        wrong_answers = [qa for qa in questions_analysis if not qa["is_correct"]]
        
        language = profile_data.get("preferred_language", "English")
        grade = profile_data.get("grade_level", "6th")
        name = profile_data.get("name", "Student")
        
        prompt = f"""You are DigiMasterJi, an educational AI assistant. Generate a quiz summary for a student.

Student Profile:
- Name: {name}
- Grade: {grade}
- Preferred Language: {language}

Quiz Details:
- Topic: {quiz.topic}
- Score: {quiz_result.get('score', 0)}%
- Correct: {quiz_result.get('correct_count', 0)} out of {len(quiz.questions)}

Questions the student got wrong:
{json.dumps(wrong_answers, indent=2) if wrong_answers else "None - Perfect score!"}

Historical Performance:
- Total Quizzes Taken: {history_analysis.get('total_quizzes', 0)}
- Overall Average: {history_analysis.get('overall_average', 0)}%
- Recent Trend: {history_analysis.get('recent_trend', 'neutral')}

Generate a JSON response with this EXACT structure (no markdown, pure JSON):
{{
    "performance_level": "excellent|good|needs_improvement|poor",
    "summary_text": "A 2-3 sentence summary of how the student performed on this quiz",
    "summary_text_hindi": "Same summary in Hindi",
    "topics_to_review": ["List of specific topics the student should review based on wrong answers"],
    "encouragement": "A short encouraging message for the student",
    "encouragement_hindi": "Same encouragement in Hindi",
    "study_tips": ["2-3 specific study tips related to the wrong answers"],
    "concepts_explained": [
        {{
            "concept": "Name of a concept the student struggled with",
            "explanation": "Brief, simple explanation suitable for {grade} grade",
            "explanation_hindi": "Same explanation in Hindi"
        }}
    ],
    "next_steps": "What the student should focus on next"
}}

Important:
- Keep explanations simple and suitable for {grade} grade students
- Use encouraging language
- Be specific about what concepts to review based on the actual wrong answers
- Provide practical study tips
- Return ONLY valid JSON, no other text"""

        try:
            result = await self.llm_service.generate(
                prompt=prompt,
                temperature=0.7,
                max_tokens=2048
            )
            
            if not result.get("success"):
                logger.error(f"[QUIZ SUMMARY] LLM generation failed: {result.get('error')}")
                return self._get_fallback_summary(quiz_result, wrong_answers)
            
            response_text = result.get("response", "")
            
            # Parse JSON from response
            summary = self._parse_json_response(response_text)
            if summary:
                summary["quiz_id"] = str(quiz.id)
                summary["topic"] = quiz.topic
                summary["score"] = quiz_result.get('score', 0)
                summary["correct_count"] = quiz_result.get('correct_count', 0)
                summary["total_questions"] = len(quiz.questions)
                summary["generated_at"] = datetime.utcnow().isoformat()
                return summary
            
            return self._get_fallback_summary(quiz_result, wrong_answers)
            
        except Exception as e:
            logger.error(f"[QUIZ SUMMARY] Error in LLM generation: {e}")
            return self._get_fallback_summary(quiz_result, wrong_answers)
    
    async def _generate_insights_with_llm(
        self,
        profile_data: Dict[str, Any],
        history_analysis: Dict[str, Any],
        quizzes: List
    ) -> Optional[Dict[str, Any]]:
        """Generate comprehensive learning insights using LLM."""
        
        language = profile_data.get("preferred_language", "English")
        grade = profile_data.get("grade_level", "6th")
        name = profile_data.get("name", "Student")
        
        # Build subject breakdown
        subject_breakdown = []
        for subject, stats in history_analysis.get("subject_stats", {}).items():
            subject_breakdown.append({
                "subject": subject,
                "quizzes_taken": stats["total_quizzes"],
                "average_score": round(stats["average_score"], 1),
                "topics_covered": stats["topics"][:5],  # Limit topics
                "weak_questions_count": len(stats.get("weak_questions", []))
            })
        
        # Get sample weak questions
        weak_questions_sample = history_analysis.get("weak_questions", [])[:10]
        
        prompt = f"""You are DigiMasterJi, an educational AI assistant. Generate comprehensive learning insights for a student.

Student Profile:
- Name: {name}
- Grade: {grade}
- Preferred Language: {language}

Performance Overview:
- Total Quizzes: {history_analysis.get('total_quizzes', 0)}
- Overall Average: {history_analysis.get('overall_average', 0)}%
- Performance Trend: {history_analysis.get('recent_trend', 'neutral')}
- Strong Topics: {', '.join(history_analysis.get('strong_topics', [])) or 'None identified yet'}

Subject-wise Breakdown:
{json.dumps(subject_breakdown, indent=2)}

Sample Questions Student Got Wrong:
{json.dumps(weak_questions_sample, indent=2)}

Generate a JSON response with this EXACT structure (no markdown, pure JSON):
{{
    "overall_assessment": {{
        "level": "excellent|good|average|needs_improvement",
        "summary": "2-3 sentence overall assessment",
        "summary_hindi": "Same in Hindi"
    }},
    "subject_insights": [
        {{
            "subject": "Subject name",
            "status": "strong|average|weak",
            "score_average": 0,
            "improvement_areas": ["List of specific topics/concepts to improve"],
            "recommendation": "Specific recommendation for this subject",
            "recommendation_hindi": "Same in Hindi"
        }}
    ],
    "weak_topics_explanation": [
        {{
            "topic": "Topic name",
            "subject": "Subject",
            "why_important": "Why this topic matters",
            "simple_explanation": "Brief, grade-appropriate explanation",
            "simple_explanation_hindi": "Same in Hindi",
            "practice_tip": "How to practice this topic"
        }}
    ],
    "strengths": [
        {{
            "area": "Area of strength",
            "praise": "Encouraging message about this strength",
            "praise_hindi": "Same in Hindi"
        }}
    ],
    "weekly_goals": [
        {{
            "goal": "Specific, achievable goal",
            "goal_hindi": "Same in Hindi",
            "subject": "Related subject"
        }}
    ],
    "motivational_message": "An encouraging message based on their progress",
    "motivational_message_hindi": "Same in Hindi"
}}

Important:
- Be specific based on the actual data provided
- Keep all explanations suitable for {grade} grade students
- Provide actionable, practical recommendations
- Be encouraging while honest about areas needing improvement
- Return ONLY valid JSON, no other text"""

        try:
            result = await self.llm_service.generate(
                prompt=prompt,
                temperature=0.7,
                max_tokens=3000
            )
            
            if not result.get("success"):
                logger.error(f"[LEARNING INSIGHTS] LLM generation failed: {result.get('error')}")
                return self._get_fallback_insights(history_analysis)
            
            response_text = result.get("response", "")
            
            # Parse JSON from response
            insights = self._parse_json_response(response_text)
            if insights:
                insights["has_data"] = True
                insights["profile_name"] = name
                insights["grade_level"] = grade
                insights["total_quizzes"] = history_analysis.get("total_quizzes", 0)
                insights["overall_average"] = history_analysis.get("overall_average", 0)
                insights["performance_trend"] = history_analysis.get("recent_trend", "neutral")
                insights["generated_at"] = datetime.utcnow().isoformat()
                insights["analysis_period_days"] = 30
                return insights
            
            return self._get_fallback_insights(history_analysis)
            
        except Exception as e:
            logger.error(f"[LEARNING INSIGHTS] Error in LLM generation: {e}")
            return self._get_fallback_insights(history_analysis)
    
    def _parse_json_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parse JSON from LLM response, handling markdown code blocks."""
        try:
            # Try direct JSON parse first
            return json.loads(response_text.strip())
        except json.JSONDecodeError:
            pass
        
        # Try extracting from markdown code block
        import re
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
        if json_match:
            try:
                return json.loads(json_match.group(1).strip())
            except json.JSONDecodeError:
                pass
        
        # Try finding JSON object in text
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        logger.error(f"[QUIZ SUMMARY] Failed to parse JSON from response: {response_text[:500]}")
        return None
    
    def _get_fallback_summary(self, quiz_result: Dict[str, Any], wrong_answers: List) -> Dict[str, Any]:
        """Generate fallback summary when LLM fails."""
        score = quiz_result.get('score', 0)
        
        if score >= 90:
            level = "excellent"
            msg = "Excellent work! You've demonstrated a strong understanding of this topic."
            msg_hi = "शानदार काम! आपने इस विषय की बहुत अच्छी समझ दिखाई है।"
        elif score >= 70:
            level = "good"
            msg = "Good job! You're on the right track. Review the topics you missed."
            msg_hi = "अच्छा काम! आप सही रास्ते पर हैं। जो विषय छूट गए उनकी समीक्षा करें।"
        elif score >= 50:
            level = "needs_improvement"
            msg = "Keep practicing! Focus on the concepts you found challenging."
            msg_hi = "अभ्यास जारी रखें! जो अवधारणाएं कठिन लगीं उन पर ध्यान दें।"
        else:
            level = "poor"
            msg = "Don't give up! Review the basics and try again. Every attempt helps you learn."
            msg_hi = "हार मत मानो! मूल बातें दोहराएं और फिर से कोशिश करें। हर प्रयास सीखने में मदद करता है।"
        
        return {
            "performance_level": level,
            "summary_text": msg,
            "summary_text_hindi": msg_hi,
            "topics_to_review": [wa["question"][:50] + "..." for wa in wrong_answers[:3]] if wrong_answers else [],
            "encouragement": "Keep learning! Every quiz makes you smarter.",
            "encouragement_hindi": "सीखते रहो! हर क्विज़ आपको होशियार बनाती है।",
            "study_tips": [
                "Review your notes on topics you got wrong",
                "Practice similar problems",
                "Ask for help if you don't understand a concept"
            ],
            "concepts_explained": [],
            "next_steps": "Review the topics you missed and try another quiz tomorrow!",
            "score": score,
            "correct_count": quiz_result.get('correct_count', 0),
            "total_questions": quiz_result.get('total_questions', 0),
            "generated_at": datetime.utcnow().isoformat()
        }
    
    def _get_fallback_insights(self, history_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate fallback insights when LLM fails."""
        avg = history_analysis.get("overall_average", 0)
        total_quizzes = history_analysis.get("total_quizzes", 0)
        trend = history_analysis.get("recent_trend", "neutral")
        
        if avg >= 80:
            level = "excellent"
            summary = "You're doing great! Keep up the excellent work."
            summary_hindi = "आप बहुत अच्छा कर रहे हैं! इसी तरह मेहनत करते रहें।"
        elif avg >= 60:
            level = "good"
            summary = "You're making good progress. Focus on your weaker subjects."
            summary_hindi = "आप अच्छी प्रगति कर रहे हैं। अपने कमज़ोर विषयों पर ध्यान दें।"
        elif avg >= 40:
            level = "average"
            summary = "Keep practicing! There's room for improvement in several areas."
            summary_hindi = "अभ्यास जारी रखें! कई क्षेत्रों में सुधार की गुंजाइश है।"
        else:
            level = "needs_improvement"
            summary = "Let's work together to improve your understanding. Practice makes perfect!"
            summary_hindi = "आइए मिलकर आपकी समझ को बेहतर बनाएं। अभ्यास से निपुणता आती है!"
        
        # Build subject insights from history if available
        subject_insights = []
        for subject, stats in history_analysis.get("subject_stats", {}).items():
            avg_score = stats.get("average_score", 0)
            status = "strong" if avg_score >= 70 else ("average" if avg_score >= 50 else "weak")
            subject_insights.append({
                "subject": subject,
                "status": status,
                "score_average": round(avg_score, 1),
                "performance_trend": trend,
                "improvement_areas": stats.get("topics", [])[:3] if avg_score < 70 else [],
                "strong_areas": stats.get("topics", [])[:3] if avg_score >= 70 else [],
                "recommendation": f"Continue practicing {subject} topics.",
                "recommendation_hindi": f"{subject} के विषयों का अभ्यास जारी रखें।"
            })
        
        return {
            "has_data": True,
            "profile_name": None,  # Will be set by caller
            "grade_level": None,   # Will be set by caller
            "total_quizzes": total_quizzes,
            "overall_average": avg,
            "performance_trend": trend,
            "overall_assessment": {
                "level": level,
                "summary": summary,
                "summary_hindi": summary_hindi
            },
            "subject_insights": subject_insights,
            "weak_topics_explanation": [],  # Empty in fallback - requires LLM
            "strengths": [
                {
                    "area": "Dedication",
                    "praise": "You're taking quizzes regularly. Keep it up!",
                    "praise_hindi": "आप नियमित रूप से क्विज़ दे रहे हैं। बहुत अच्छा!"
                }
            ] if total_quizzes > 0 else [],
            "weekly_goals": [
                {"goal": "Complete one quiz every day", "goal_hindi": "हर दिन एक क्विज़ पूरा करें", "subject": "General"},
                {"goal": "Review wrong answers from past quizzes", "goal_hindi": "पिछले क्विज़ के गलत उत्तरों की समीक्षा करें", "subject": "General"}
            ],
            "personalized_recommendations": [
                "Practice regularly with daily quizzes",
                "Review the topics where you made mistakes",
                "Don't hesitate to ask questions when you don't understand"
            ],
            "motivational_message": "Every day is a new chance to learn something new!",
            "motivational_message_hindi": "हर दिन कुछ नया सीखने का मौका है!",
            "generated_at": datetime.utcnow().isoformat(),
            "analysis_period_days": 30,
            "rag_enhanced": False
        }


# Create singleton instance
quiz_summary_service = QuizSummaryService()
