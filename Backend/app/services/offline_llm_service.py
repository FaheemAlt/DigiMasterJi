"""
Offline LLM Service - Local Gemma3 270M Model for Offline Chat
===============================================================
This service provides offline chat capabilities using a smaller, 
more efficient Gemma3 270M parameter model when network is unavailable.

Key Features:
- Lightweight 270M parameter model for quick responses
- English-only responses for offline mode
- No RAG or web search - pure local LLM
- Optimized for low-resource environments

DigiMasterJi - Multilingual AI Tutor for Rural Education
"""

import httpx
from typing import Optional, AsyncGenerator, Dict, Any, List
import json
import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class OfflineLLMService:
    """
    Service for offline chat using Gemma3 270M parameter model.
    Provides basic educational responses without RAG or web search.
    All responses are in English for offline mode.
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: float = 60.0
    ):
        """
        Initialize the offline LLM service.
        
        Args:
            base_url: Ollama server URL (defaults to env or localhost:11434)
            model_name: Offline model to use (defaults to gemma3:1b for 270M params)
            timeout: Request timeout in seconds (shorter for offline)
        """
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        # Use the smaller Gemma3 model for offline - gemma3:1b is approximately 270M parameters
        self.model_name = model_name or os.getenv("OLLAMA_OFFLINE_MODEL", "gemma3:1b")
        self.timeout = timeout
        self.is_available = False
        
        # System prompt for offline mode - English only, simpler responses
        self.offline_system_prompt = """You are DigiMasterJi, a helpful AI tutor for students in India.

=== CRITICAL RESTRICTION ===
You are STRICTLY an educational AI tutor. You can ONLY help with:
- Science (Physics, Chemistry, Biology, Environmental Science)
- Technology (Computers, Programming, Digital Literacy)
- Engineering concepts and problem-solving
- Mathematics (Arithmetic, Algebra, Geometry, Calculus, Statistics)
- General educational topics (Study skills, Exam preparation, Learning strategies)

If a student asks about ANYTHING that is NOT related to education, academics, STEM, or learning, you MUST respond with:
"I'm sorry, but I'm an educational AI tutor designed to help you with your studies. I can only assist with Science, Technology, Engineering, Mathematics, and educational topics. Please feel free to ask me any question about your academics, and I'll be happy to help!"

Topics you MUST DECLINE: Entertainment, movies, personal advice, relationships, politics, jokes, games, cooking, health advice, legal/financial advice, or any inappropriate content. ALWAYS redirect to educational topics.
=== END RESTRICTION ===

OFFLINE MODE RULES:
1. LANGUAGE: You MUST respond ONLY in English. Do not use Hindi or other Indian languages.
2. SIMPLICITY: Keep explanations simple and clear. Use short sentences.
3. ENCOURAGEMENT: Be friendly and encouraging. Celebrate learning!
4. EXAMPLES: Use simple, everyday examples students can relate to.
5. STEP-BY-STEP: Break down complex concepts into small steps.
6. VERIFICATION: Ask if the student understands before moving on.
7. CONCISENESS: Be SHORT and DIRECT. No filler phrases, no verbose introductions. Get to the point immediately.

Note: You are running in offline mode with limited capabilities. Focus on core concepts and clear explanations.

Start your responses with acknowledgment of the question, then provide a clear, educational answer."""

    async def check_availability(self) -> Dict[str, Any]:
        """
        Check if the offline model is available locally.
        
        Returns:
            Dictionary with availability status
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    model_names = [m.get("name", "") for m in models]
                    
                    # Check if offline model is available
                    model_available = any(self.model_name in m for m in model_names)
                    self.is_available = model_available
                    
                    return {
                        "status": "available" if model_available else "model_not_found",
                        "server": self.base_url,
                        "offline_model": self.model_name,
                        "model_available": model_available,
                        "available_models": model_names
                    }
                return {"status": "server_error", "error": f"Status code: {response.status_code}"}
        except httpx.ConnectError:
            self.is_available = False
            return {
                "status": "unavailable",
                "error": f"Cannot connect to Ollama at {self.base_url}"
            }
        except Exception as e:
            self.is_available = False
            return {"status": "error", "error": str(e)}

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.5,
        max_tokens: int = 512
    ) -> Dict[str, Any]:
        """
        Generate a response using the offline model.
        
        Args:
            prompt: User's input message
            temperature: Lower temperature for more focused responses
            max_tokens: Shorter responses for offline mode
            
        Returns:
            Dictionary containing the response and metadata
        """
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "system": self.offline_system_prompt,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
            "stream": False
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                
                return {
                    "success": True,
                    "response": result.get("response", ""),
                    "model": result.get("model", self.model_name),
                    "total_duration": result.get("total_duration", 0),
                    "offline_mode": True
                }
                
        except httpx.TimeoutException:
            return {
                "success": False,
                "error": "Request timed out. The offline model may be loading.",
                "offline_mode": True
            }
        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "error": f"HTTP error: {e.response.status_code}",
                "offline_mode": True
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "offline_mode": True
            }

    async def generate_stream(
        self,
        prompt: str,
        temperature: float = 0.5,
        max_tokens: int = 512
    ) -> AsyncGenerator[str, None]:
        """
        Stream a response from the offline model token by token.
        
        Yields:
            Individual response tokens as they are generated
        """
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "system": self.offline_system_prompt,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
            "stream": True
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/generate",
                    json=payload
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                if "response" in data:
                                    yield data["response"]
                                if data.get("done", False):
                                    break
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            logger.error(f"[OFFLINE LLM] Stream error: {e}")
            yield f"[Offline mode error: {str(e)}]"

    def build_offline_prompt(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Build a prompt for offline mode with limited context.
        
        Args:
            user_message: The user's current message
            conversation_history: Recent conversation history (limited for offline)
            
        Returns:
            Formatted prompt string
        """
        prompt_parts = []
        
        # Add limited conversation history (last 3 exchanges only for offline)
        if conversation_history:
            recent_history = conversation_history[-6:]  # Last 3 exchanges (6 messages)
            if recent_history:
                prompt_parts.append("=== Recent Conversation ===")
                for msg in recent_history:
                    role = "Student" if msg.get("role") == "user" else "Tutor"
                    content = msg.get("content", "")[:200]  # Truncate for offline
                    prompt_parts.append(f"{role}: {content}")
                prompt_parts.append("=== End of Recent Conversation ===\n")
        
        # Add current question
        prompt_parts.append(f"Student's Question: {user_message}")
        prompt_parts.append("\nProvide a helpful, educational response in English:")
        
        return "\n".join(prompt_parts)


# Singleton instance for easy importing
offline_llm_service = OfflineLLMService()


# Test function
async def test_offline_service():
    """Test the offline LLM service."""
    print("=" * 60)
    print("Testing Offline LLM Service (Gemma3 270M)")
    print("=" * 60)
    
    service = OfflineLLMService()
    
    # Test 1: Check availability
    print("\n1. Checking offline model availability...")
    availability = await service.check_availability()
    print(f"   Status: {availability.get('status')}")
    print(f"   Offline model: {availability.get('offline_model')}")
    print(f"   Available: {availability.get('model_available')}")
    
    if not availability.get('model_available'):
        print(f"\n   ⚠️  Offline model not available. To install:")
        print(f"   Run: ollama pull {service.model_name}")
        return
    
    # Test 2: Simple generation
    print("\n2. Testing offline generation...")
    test_prompt = service.build_offline_prompt("What is photosynthesis?")
    result = await service.generate(test_prompt)
    
    if result.get("success"):
        print(f"   Response: {result.get('response', '')[:200]}...")
        print(f"   Offline mode: {result.get('offline_mode')}")
    else:
        print(f"   Error: {result.get('error')}")
    
    print("\n" + "=" * 60)
    print("Offline LLM Service test completed!")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_offline_service())
