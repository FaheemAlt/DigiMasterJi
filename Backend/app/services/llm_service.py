"""
LLM Service - AWS Bedrock Integration for Amazon Nova Lite
=====================================================================
This service handles communication with Amazon Bedrock
for generating AI tutor responses in multiple Indian languages.

DigiMasterJi - Multilingual AI Tutor for Rural Education
"""

import boto3
from botocore.exceptions import ClientError
from typing import Optional, AsyncGenerator, Dict, Any, List
import json
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

# Thread pool for running sync boto3 calls in async context
_executor = ThreadPoolExecutor(max_workers=4)


class LLMService:
    """
    Service for interacting with Amazon Bedrock's LLM API.
    Uses Amazon Nova Lite for multilingual STEM tutoring.
    """
    
    def __init__(
        self,
        model_id: Optional[str] = None,
        region: Optional[str] = None,
        timeout: float = 120.0
    ):
        """
        Initialize the LLM service.
        
        Args:
            model_id: Bedrock model ID (defaults to us.amazon.nova-lite-v1:0)
            region: AWS region for Bedrock
            timeout: Request timeout in seconds
        """
        default_model = "us.amazon.nova-lite-v1:0"
        self.model_id = model_id or os.getenv("BEDROCK_MODEL_ID", default_model)
        
        # Ensure we use cross-region inference profile format
        if self.model_id.startswith("meta.") and not self.model_id.startswith("us."):
            self.model_id = f"us.{self.model_id}"
        self.region = region or os.getenv("AWS_REGION", "us-east-1")
        self.timeout = timeout
        
        # Initialize Bedrock Runtime client
        self._client = None
        
        # System prompt for STEM tutoring in regional languages
        self.default_system_prompt = """You are DigiMasterJi, a friendly and patient AI tutor designed to teach STEM concepts to rural and under-resourced students in India. 

Key Guidelines:
1. LANGUAGE: Respond in the same language the student uses. Support Hindi, English, and other Indian regional languages.
2. SIMPLICITY: Explain concepts in simple terms with relatable real-world examples from rural Indian life.
3. ENCOURAGEMENT: Be encouraging and supportive. Celebrate small wins.
4. STEP-BY-STEP: Break down complex problems into small, manageable steps.
5. VERIFICATION: Ask follow-up questions to ensure understanding.
6. CULTURAL CONTEXT: Use examples relevant to Indian students (farming, local festivals, everyday life).

Remember: Many students may have limited prior exposure to these concepts. Be patient and thorough."""

    @property
    def client(self):
        """Lazy initialization of Bedrock Runtime client."""
        if self._client is None:
            self._client = boto3.client(
                "bedrock-runtime",
                region_name=self.region
            )
        return self._client

    async def check_health(self) -> Dict[str, Any]:
        """
        Check if Bedrock service is accessible.
        
        Returns:
            Dictionary with health status and model info
        """
        try:
            # Try to list foundation models to verify access
            bedrock_client = boto3.client("bedrock", region_name=self.region)
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                _executor,
                lambda: bedrock_client.list_foundation_models(
                    byProvider="meta"
                )
            )
            
            models = response.get("modelSummaries", [])
            model_ids = [m.get("modelId", "") for m in models]
            
            return {
                "status": "healthy",
                "service": "Amazon Bedrock",
                "region": self.region,
                "available_models": model_ids[:10],  # Limit to first 10
                "target_model": self.model_id,
                "model_available": any(self.model_id in m for m in model_ids)
            }
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            return {
                "status": "unhealthy",
                "error": f"Bedrock error ({error_code}): {str(e)}"
            }
        except Exception as e:
            return {
                "status": "unhealthy", 
                "error": f"Connection error: {str(e)}"
            }

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[List[int]] = None,  # Kept for API compatibility
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Generate a response from the LLM using Bedrock Converse API.
        
        Args:
            prompt: User's input message
            system_prompt: Custom system prompt (uses default if not provided)
            context: Ignored (kept for API compatibility with Ollama version)
            temperature: Creativity of response (0.0 = deterministic, 1.0 = creative)
            max_tokens: Maximum response length
            stream: Whether to stream (not supported in this method, use generate_stream)
            
        Returns:
            Dictionary containing the response and metadata
        """
        system = system_prompt or self.default_system_prompt
        
        # Build messages for Converse API
        messages = [
            {
                "role": "user",
                "content": [{"text": prompt}]
            }
        ]
        
        # System prompt as system parameter
        system_prompts = [{"text": system}]
        
        # Inference configuration
        inference_config = {
            "temperature": temperature,
            "maxTokens": max_tokens
        }
        
        try:
            loop = asyncio.get_event_loop()
            
            response = await loop.run_in_executor(
                _executor,
                lambda: self.client.converse(
                    modelId=self.model_id,
                    messages=messages,
                    system=system_prompts,
                    inferenceConfig=inference_config
                )
            )
            
            # Extract response text
            output = response.get("output", {})
            message = output.get("message", {})
            content_blocks = message.get("content", [])
            response_text = ""
            
            for block in content_blocks:
                if "text" in block:
                    response_text += block["text"]
            
            # Get usage stats
            usage = response.get("usage", {})
            
            return {
                "success": True,
                "response": response_text,
                "context": [],  # Bedrock doesn't use context tokens like Ollama
                "model": self.model_id,
                "total_duration": 0,  # Not provided by Bedrock
                "eval_count": usage.get("outputTokens", 0),
                "input_tokens": usage.get("inputTokens", 0),
                "stop_reason": response.get("stopReason", "")
            }
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.error(f"[LLM] Bedrock error: {error_code} - {e}")
            
            if error_code == "ThrottlingException":
                return {
                    "success": False,
                    "error": "Request throttled. Please try again in a moment."
                }
            elif error_code == "ValidationException":
                return {
                    "success": False,
                    "error": f"Invalid request: {str(e)}"
                }
            else:
                return {
                    "success": False,
                    "error": f"Bedrock error ({error_code}): {str(e)}"
                }
                
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "Request timed out. The model may be processing a complex query."
            }
        except Exception as e:
            logger.error(f"[LLM] Unexpected error: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[List[int]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> AsyncGenerator[str, None]:
        """
        Stream a response from the LLM using Bedrock ConverseStream API.
        
        Yields:
            Individual response tokens as they are generated
        """
        system = system_prompt or self.default_system_prompt
        
        # Build messages for Converse API
        messages = [
            {
                "role": "user",
                "content": [{"text": prompt}]
            }
        ]
        
        system_prompts = [{"text": system}]
        
        inference_config = {
            "temperature": temperature,
            "maxTokens": max_tokens
        }
        
        try:
            # Use converseStream for streaming
            loop = asyncio.get_event_loop()
            
            response = await loop.run_in_executor(
                _executor,
                lambda: self.client.converse_stream(
                    modelId=self.model_id,
                    messages=messages,
                    system=system_prompts,
                    inferenceConfig=inference_config
                )
            )
            
            # Process the event stream
            stream = response.get("stream")
            if stream:
                for event in stream:
                    if "contentBlockDelta" in event:
                        delta = event["contentBlockDelta"].get("delta", {})
                        if "text" in delta:
                            yield delta["text"]
                    elif "messageStop" in event:
                        break
                        
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.error(f"[LLM STREAM] Bedrock error: {error_code}")
            yield f"[Error: {str(e)}]"
        except Exception as e:
            logger.error(f"[LLM STREAM] Unexpected error: {e}")
            yield f"[Error: {str(e)}]"

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> Dict[str, Any]:
        """
        Chat completion with message history using Bedrock Converse API.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
                     roles can be: 'system', 'user', 'assistant'
            temperature: Creativity of response
            max_tokens: Maximum response length
            
        Returns:
            Dictionary containing the assistant's response
        """
        # Extract system message if present
        system_content = self.default_system_prompt
        chat_messages = []
        
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            
            if role == "system":
                system_content = content
            elif role in ["user", "assistant"]:
                chat_messages.append({
                    "role": role,
                    "content": [{"text": content}]
                })
        
        # Ensure we have at least one user message
        if not chat_messages:
            return {
                "success": False,
                "error": "No user or assistant messages provided"
            }
        
        system_prompts = [{"text": system_content}]
        
        inference_config = {
            "temperature": temperature,
            "maxTokens": max_tokens
        }
        
        try:
            loop = asyncio.get_event_loop()
            
            response = await loop.run_in_executor(
                _executor,
                lambda: self.client.converse(
                    modelId=self.model_id,
                    messages=chat_messages,
                    system=system_prompts,
                    inferenceConfig=inference_config
                )
            )
            
            # Extract response
            output = response.get("output", {})
            message = output.get("message", {})
            content_blocks = message.get("content", [])
            response_text = ""
            
            for block in content_blocks:
                if "text" in block:
                    response_text += block["text"]
            
            usage = response.get("usage", {})
            
            return {
                "success": True,
                "message": {
                    "role": "assistant",
                    "content": response_text
                },
                "model": self.model_id,
                "total_duration": 0,
                "input_tokens": usage.get("inputTokens", 0),
                "output_tokens": usage.get("outputTokens", 0)
            }
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.error(f"[LLM CHAT] Bedrock error: {error_code}")
            return {
                "success": False,
                "error": f"Bedrock error ({error_code}): {str(e)}"
            }
        except Exception as e:
            logger.error(f"[LLM CHAT] Unexpected error: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Singleton instance for easy importing
llm_service = LLMService()


# Test function
async def test_llm_service():
    """Test the LLM service connection and generation."""
    print("=" * 60)
    print("Testing LLM Service (Amazon Bedrock + Amazon Nova Lite)")
    print("=" * 60)
    
    service = LLMService()
    
    # Test 1: Health check
    print("\n1. Checking Bedrock service health...")
    health = await service.check_health()
    print(f"   Status: {health.get('status')}")
    if health.get('status') == 'healthy':
        print(f"   Region: {health.get('region')}")
        print(f"   Target model ({service.model_id}) available: {health.get('model_available')}")
    else:
        print(f"   Error: {health.get('error')}")
        print("\n   ⚠️  To fix this:")
        print("   1. Ensure AWS credentials are configured")
        print("   2. Verify Bedrock access is enabled in your AWS account")
        print(f"   3. Request access to model: {service.model_id}")
        return
    
    # Test 2: Simple generation
    print("\n2. Testing simple generation...")
    test_prompt = "What is photosynthesis? Explain in simple Hindi."
    print(f"   Prompt: {test_prompt}")
    
    result = await service.generate(test_prompt)
    if result.get("success"):
        response = result.get('response', '')
        print(f"   Response: {response[:200]}..." if len(response) > 200 else f"   Response: {response}")
        print(f"   Input tokens: {result.get('input_tokens', 0)}")
        print(f"   Output tokens: {result.get('eval_count', 0)}")
    else:
        print(f"   Error: {result.get('error')}")
    
    print("\n" + "=" * 60)
    print("LLM Service test completed!")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_llm_service())
