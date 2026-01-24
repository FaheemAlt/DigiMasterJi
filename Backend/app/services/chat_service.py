"""
Chat Service - RAG-Enhanced LLM Response Generation
=====================================================
This service orchestrates the chat pipeline:
1. Retrieve conversation history for context
2. Generate embedding for user query
3. Perform vector search for relevant knowledge
4. Construct prompt with context + RAG results + user query
5. Generate response using Ollama LLM

DigiMasterJi - Multilingual AI Tutor for Rural Education
"""

from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime
import os
import logging
from dotenv import load_dotenv

from app.services.llm_service import llm_service
from app.services.rag_service import rag_service
from app.database.knowledge_base import vector_search
from app.database.messages import MessagesDatabase
from app.models.message import MessageInDB

load_dotenv()

# Configure logging for chat flow tracing
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
logger.setLevel(logging.INFO)


# ============================================================================
# Configuration - All configurable parameters in one place
# ============================================================================

# Number of previous messages to include as conversation context
CONVERSATION_HISTORY_LIMIT = int(os.getenv("CHAT_HISTORY_LIMIT", "10"))

# Number of RAG chunks to retrieve for context
RAG_CHUNKS_LIMIT = int(os.getenv("RAG_CHUNKS_LIMIT", "5"))

# Minimum similarity score for RAG results (0.0 to 1.0)
RAG_MIN_SCORE = float(os.getenv("RAG_MIN_SCORE", "0.3"))

# Maximum tokens for RAG context in prompt
RAG_MAX_CONTEXT_TOKENS = int(os.getenv("RAG_MAX_CONTEXT_TOKENS", "1500"))

# LLM generation settings
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1024"))


class ChatService:
    """
    Service for handling RAG-enhanced chat interactions.
    Connects user input → vector search → Ollama prompt → response.
    """
    
    def __init__(
        self,
        history_limit: int = CONVERSATION_HISTORY_LIMIT,
        rag_chunks_limit: int = RAG_CHUNKS_LIMIT,
        rag_min_score: float = RAG_MIN_SCORE,
        temperature: float = LLM_TEMPERATURE,
        max_tokens: int = LLM_MAX_TOKENS
    ):
        """
        Initialize the chat service.
        
        Args:
            history_limit: Number of previous messages to include as context
            rag_chunks_limit: Number of RAG chunks to retrieve
            rag_min_score: Minimum similarity score for RAG results
            temperature: LLM creativity (0.0-1.0)
            max_tokens: Maximum response length
        """
        self.history_limit = history_limit
        self.rag_chunks_limit = rag_chunks_limit
        self.rag_min_score = rag_min_score
        self.temperature = temperature
        self.max_tokens = max_tokens
    
    async def get_conversation_context(
        self,
        conversation_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """
        Retrieve recent conversation history formatted for LLM context.
        
        Args:
            conversation_id: The conversation ID
            limit: Override for history limit
            
        Returns:
            List of message dicts with 'role' and 'content' keys
        """
        limit = limit or self.history_limit
        
        try:
            messages = await MessagesDatabase.get_messages_by_conversation(
                conversation_id,
                limit=limit
            )
            
            logger.info(f"[CHAT FLOW] Retrieved {len(messages)} messages from MongoDB conversation history")
            
            # Format messages for LLM chat format
            formatted = []
            for msg in messages:
                formatted.append({
                    "role": msg.role,
                    "content": msg.content
                })
            
            return formatted
        except Exception as e:
            print(f"Error retrieving conversation context: {e}")
            return []
    
    async def search_knowledge_base(
        self,
        query: str,
        limit: Optional[int] = None,
        subject: Optional[str] = None,
        language: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search the knowledge base for relevant content.
        
        Args:
            query: User's question/query
            limit: Number of chunks to retrieve
            subject: Optional subject filter
            language: Optional language filter
            
        Returns:
            List of relevant knowledge chunks with scores
        """
        limit = limit or self.rag_chunks_limit
        
        try:
            logger.info(f"[CHAT FLOW] Searching RAG knowledge base for: '{query[:50]}...'")
            
            # Generate embedding for the query
            query_embedding = rag_service.generate_embedding(query)
            
            # Perform vector search
            results = await vector_search(
                query_embedding=query_embedding,
                limit=limit,
                subject=subject,
                language=language
            )
            
            # Filter by minimum score
            filtered_results = [
                r for r in results 
                if r.get("score", 0) >= self.rag_min_score
            ]
            
            logger.info(f"[CHAT FLOW] RAG search returned {len(results)} results, {len(filtered_results)} after filtering (min_score={self.rag_min_score})")
            
            return filtered_results
        except Exception as e:
            print(f"Error searching knowledge base: {e}")
            return []
    
    def build_rag_context(self, rag_results: List[Dict[str, Any]]) -> str:
        """
        Build a formatted context string from RAG results.
        
        Args:
            rag_results: List of knowledge chunks from vector search
            
        Returns:
            Formatted context string for the prompt
        """
        if not rag_results:
            return ""
        
        context_parts = []
        context_parts.append("=== Relevant Learning Material ===")
        
        for i, chunk in enumerate(rag_results, 1):
            title = chunk.get("title", "Untitled")
            content = chunk.get("content_chunk", "")
            subject = chunk.get("subject", "General")
            
            # Truncate content if too long (rough token estimate: 4 chars per token)
            max_chars = (RAG_MAX_CONTEXT_TOKENS // len(rag_results)) * 4
            if len(content) > max_chars:
                content = content[:max_chars] + "..."
            
            context_parts.append(f"\n[Source {i}: {subject} - {title}]")
            context_parts.append(content)
        
        context_parts.append("\n=== End of Learning Material ===\n")
        
        return "\n".join(context_parts)
    
    def build_conversation_context(
        self,
        history: List[Dict[str, str]]
    ) -> str:
        """
        Build a formatted conversation history string.
        
        Args:
            history: List of previous messages
            
        Returns:
            Formatted conversation context
        """
        if not history:
            return ""
        
        context_parts = ["=== Previous Conversation ==="]
        
        for msg in history:
            role = "Student" if msg["role"] == "user" else "DigiMasterJi"
            context_parts.append(f"{role}: {msg['content']}")
        
        context_parts.append("=== End of Previous Conversation ===\n")
        
        return "\n".join(context_parts)
    
    def build_system_prompt(self, has_rag_context: bool = False, profile_data: Optional[Dict[str, Any]] = None) -> str:
        """
        Build the system prompt for DigiMasterJi.
        
        Args:
            has_rag_context: Whether RAG context is available
            profile_data: Optional student profile data for personalization
            
        Returns:
            System prompt string
        """
        base_prompt = """You are DigiMasterJi, a friendly and patient AI tutor designed to teach STEM concepts to rural and under-resourced students in India."""

        # Add profile-specific instructions if available
        if profile_data:
            name = profile_data.get("name", "Student")
            age = profile_data.get("age")
            grade_level = profile_data.get("grade_level")
            preferred_language = profile_data.get("preferred_language", "Hindi")
            
            base_prompt += f"""

=== STUDENT PROFILE ===
- Name: {name}
- Age: {age} years old
- Grade Level: {grade_level}
- Preferred Language: {preferred_language}
=== END PROFILE ===

IMPORTANT PERSONALIZATION RULES:
1. ADDRESS THE STUDENT: You may use the student's name ({name}) occasionally to make the interaction personal and warm.

2. LANGUAGE PREFERENCE: The student's preferred language is {preferred_language}. 
   - ALWAYS respond in {preferred_language} unless the student explicitly writes in a different language.
   - If the student writes in English but their preferred language is Hindi, respond in Hindi.
   - If they specifically ask for English, then use English.

3. AGE-APPROPRIATE RESPONSES:"""
            
            if age and age <= 10:
                base_prompt += f"""
   - This is a young child ({age} years old). Use very simple words and short sentences.
   - Use fun examples like cartoons, games, animals, and toys.
   - Add encouraging emojis occasionally (🌟, 👍, 🎉).
   - Break everything into tiny, easy steps.
   - Be extra patient and encouraging."""
            elif age and age <= 13:
                base_prompt += f"""
   - This is a middle-school student ({age} years old, {grade_level}).
   - Use relatable examples from daily life, sports, and popular culture.
   - Explain concepts clearly but don't over-simplify.
   - Encourage curiosity and exploration."""
            else:
                base_prompt += f"""
   - This is an older student ({age} years old, {grade_level}).
   - Give more detailed, mature explanations.
   - Use real-world applications and career-relevant examples.
   - Be concise but thorough. Respect their intelligence."""

        base_prompt += """

Key Guidelines:
1. SIMPLICITY: Explain concepts in simple terms with relatable real-world examples from rural Indian life (farming, local markets, festivals, nature).

2. ENCOURAGEMENT: Be warm, encouraging, and supportive. Celebrate small wins. Never make students feel bad for not knowing something.

3. STEP-BY-STEP: Break down complex problems into small, manageable steps. Use numbered lists when explaining processes.

4. VERIFICATION: After explaining, ask a simple follow-up question to check understanding.

5. BREVITY: Keep responses concise but complete. Aim for 2-4 paragraphs unless the topic requires more detail.

6. EXAMPLES: Always include at least one practical example or analogy."""

        if has_rag_context:
            base_prompt += """

7. CONTEXT USAGE: You have been provided with relevant learning material. Use this information to give accurate, curriculum-aligned answers. If the learning material is relevant, incorporate it naturally into your explanation. Don't mention that you're using provided material."""

        return base_prompt
    
    def build_final_prompt(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        rag_results: List[Dict[str, Any]]
    ) -> str:
        """
        Build the complete prompt for the LLM.
        
        Args:
            user_message: The current user message
            conversation_history: Previous messages in the conversation
            rag_results: Relevant knowledge chunks from RAG
            
        Returns:
            Complete prompt string
        """
        prompt_parts = []
        
        # Add RAG context if available
        rag_context = self.build_rag_context(rag_results)
        if rag_context:
            prompt_parts.append(rag_context)
        
        # Add conversation history if available
        conv_context = self.build_conversation_context(conversation_history)
        if conv_context:
            prompt_parts.append(conv_context)
        
        # Add current user message
        prompt_parts.append(f"Student's Question: {user_message}")
        prompt_parts.append("\nDiGiMasterJi's Response:")
        
        return "\n".join(prompt_parts)
    
    async def generate_response(
        self,
        conversation_id: str,
        user_message: str,
        subject: Optional[str] = None,
        language: Optional[str] = None,
        profile_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate an AI response for a user message.
        
        This is the main method that orchestrates the full pipeline:
        1. Get conversation history
        2. Search knowledge base
        3. Build prompt with profile context
        4. Generate LLM response
        
        Args:
            conversation_id: The conversation ID
            user_message: The user's current message
            subject: Optional subject filter for RAG
            language: Optional language filter for RAG
            profile_data: Optional student profile data for personalization
            
        Returns:
            Dictionary containing:
                - success: bool
                - response: str (AI response text)
                - rag_chunks_used: int (number of RAG chunks used)
                - error: str (if success is False)
        """
        try:
            logger.info(f"[CHAT FLOW] === Starting response generation for conversation: {conversation_id} ===")
            
            # Log profile data if available
            if profile_data:
                logger.info(f"[CHAT FLOW] Profile data loaded: name={profile_data.get('name')}, age={profile_data.get('age')}, grade={profile_data.get('grade_level')}, language={profile_data.get('preferred_language')}")
            else:
                logger.warning(f"[CHAT FLOW] No profile data provided - using default system prompt")
            
            # Step 1: Get conversation history
            history = await self.get_conversation_context(conversation_id)
            
            # Step 2: Search knowledge base for relevant content
            rag_results = await self.search_knowledge_base(
                query=user_message,
                subject=subject,
                language=language
            )
            
            # Step 3: Build prompts with profile context
            logger.info(f"[CHAT FLOW] Building context: {len(history)} history messages + {len(rag_results)} RAG chunks + profile data")
            system_prompt = self.build_system_prompt(
                has_rag_context=len(rag_results) > 0,
                profile_data=profile_data
            )
            final_prompt = self.build_final_prompt(
                user_message=user_message,
                conversation_history=history,
                rag_results=rag_results
            )
            logger.info(f"[CHAT FLOW] Context built and ready to send to LLM (system prompt: {len(system_prompt)} chars, user prompt: {len(final_prompt)} chars)")
            
            # Step 4: Generate response using LLM
            logger.info(f"[CHAT FLOW] Sending request to Ollama LLM...")
            llm_result = await llm_service.generate(
                prompt=final_prompt,
                system_prompt=system_prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            if not llm_result.get("success"):
                logger.error(f"[CHAT FLOW] LLM generation failed: {llm_result.get('error')}")
                return {
                    "success": False,
                    "error": llm_result.get("error", "LLM generation failed"),
                    "rag_chunks_used": len(rag_results)
                }
            
            response_text = llm_result.get("response", "").strip()
            logger.info(f"[CHAT FLOW] LLM response received (length: {len(response_text)} chars, model: {llm_result.get('model', 'unknown')})")
            
            # Clean up response if it starts with "DigiMasterJi:" or similar
            prefixes_to_remove = [
                "DigiMasterJi:", "DigiMasterJi's Response:",
                "DiGiMasterJi:", "DiGiMasterJi's Response:"
            ]
            for prefix in prefixes_to_remove:
                if response_text.startswith(prefix):
                    response_text = response_text[len(prefix):].strip()
            
            logger.info(f"[CHAT FLOW] === Response generation complete ===")
            
            return {
                "success": True,
                "response": response_text,
                "rag_chunks_used": len(rag_results),
                "model": llm_result.get("model", "unknown"),
                "generation_time_ns": llm_result.get("total_duration", 0)
            }
            
        except Exception as e:
            print(f"Error in generate_response: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "rag_chunks_used": 0
            }
    
    async def generate_response_stream(
        self,
        conversation_id: str,
        user_message: str,
        subject: Optional[str] = None,
        language: Optional[str] = None,
        profile_data: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Generate an AI response as a stream of tokens.
        
        This is the streaming version of generate_response that yields tokens
        as they are generated by the LLM.
        
        Args:
            conversation_id: The conversation ID
            user_message: The user's current message
            subject: Optional subject filter for RAG
            language: Optional language filter for RAG
            profile_data: Optional student profile data for personalization
            
        Yields:
            Individual response tokens as they are generated
        """
        try:
            logger.info(f"[CHAT FLOW STREAM] === Starting streaming response generation for conversation: {conversation_id} ===")
            
            # Step 1: Get conversation history
            history = await self.get_conversation_context(conversation_id)
            
            # Step 2: Search knowledge base for relevant content
            rag_results = await self.search_knowledge_base(
                query=user_message,
                subject=subject,
                language=language
            )
            
            # Step 3: Build prompts with profile context
            logger.info(f"[CHAT FLOW STREAM] Building context: {len(history)} history messages + {len(rag_results)} RAG chunks")
            system_prompt = self.build_system_prompt(
                has_rag_context=len(rag_results) > 0,
                profile_data=profile_data
            )
            final_prompt = self.build_final_prompt(
                user_message=user_message,
                conversation_history=history,
                rag_results=rag_results
            )
            
            # Step 4: Stream response using LLM
            logger.info(f"[CHAT FLOW STREAM] Starting streaming from Ollama LLM...")
            
            # Track if we need to remove prefixes from the start
            prefix_removed = False
            prefixes_to_remove = [
                "DigiMasterJi:", "DigiMasterJi's Response:",
                "DiGiMasterJi:", "DiGiMasterJi's Response:"
            ]
            buffer = ""
            
            async for token in llm_service.generate_stream(
                prompt=final_prompt,
                system_prompt=system_prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            ):
                # Handle prefix removal at the start
                if not prefix_removed:
                    buffer += token
                    # Check if buffer starts with any prefix
                    for prefix in prefixes_to_remove:
                        if buffer.startswith(prefix):
                            buffer = buffer[len(prefix):].lstrip()
                            prefix_removed = True
                            if buffer:
                                yield buffer
                            buffer = ""
                            break
                    else:
                        # Check if buffer could still match a prefix
                        could_match = any(prefix.startswith(buffer) for prefix in prefixes_to_remove)
                        if not could_match:
                            prefix_removed = True
                            yield buffer
                            buffer = ""
                else:
                    yield token
            
            # Yield any remaining buffer
            if buffer:
                yield buffer
                
            logger.info(f"[CHAT FLOW STREAM] === Streaming response complete ===")
            
        except Exception as e:
            logger.error(f"[CHAT FLOW STREAM] Error in streaming: {e}")
            import traceback
            traceback.print_exc()
            yield f"[Error: {str(e)}]"

    async def check_health(self) -> Dict[str, Any]:
        """
        Check the health of all services used by chat.
        
        Returns:
            Health status dictionary
        """
        health = {
            "chat_service": "healthy",
            "llm_service": "unknown",
            "rag_service": "unknown",
            "config": {
                "history_limit": self.history_limit,
                "rag_chunks_limit": self.rag_chunks_limit,
                "rag_min_score": self.rag_min_score,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            }
        }
        
        # Check LLM service
        llm_health = await llm_service.check_health()
        health["llm_service"] = llm_health
        
        # Check RAG service
        try:
            rag_info = rag_service.get_info()
            health["rag_service"] = {
                "status": "healthy",
                **rag_info
            }
        except Exception as e:
            health["rag_service"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        return health


# Singleton instance
chat_service = ChatService()


# Test function
async def test_chat_service():
    """Test the chat service."""
    print("=" * 60)
    print("Testing Chat Service")
    print("=" * 60)
    
    service = ChatService()
    
    # Test 1: Health check
    print("\n1. Checking service health...")
    health = await service.check_health()
    print(f"   Chat Service: {health['chat_service']}")
    print(f"   LLM Service: {health['llm_service'].get('status', 'unknown')}")
    print(f"   RAG Service: {health['rag_service'].get('status', 'unknown')}")
    print(f"   Config: {health['config']}")
    
    # Test 2: Build prompts (without actual DB calls)
    print("\n2. Testing prompt building...")
    
    mock_history = [
        {"role": "user", "content": "Hello, I want to learn about photosynthesis"},
        {"role": "assistant", "content": "Namaste! I'm happy to help you learn about photosynthesis."}
    ]
    
    mock_rag = [
        {
            "title": "Photosynthesis Basics",
            "content_chunk": "Photosynthesis is the process by which plants convert sunlight into chemical energy.",
            "subject": "Biology",
            "score": 0.85
        }
    ]
    
    system_prompt = service.build_system_prompt(has_rag_context=True)
    print(f"   System prompt length: {len(system_prompt)} chars")
    
    final_prompt = service.build_final_prompt(
        user_message="What is the equation for photosynthesis?",
        conversation_history=mock_history,
        rag_results=mock_rag
    )
    print(f"   Final prompt length: {len(final_prompt)} chars")
    print(f"   Final prompt preview: {final_prompt[:200]}...")
    
    print("\n" + "=" * 60)
    print("Chat Service test completed!")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_chat_service())
