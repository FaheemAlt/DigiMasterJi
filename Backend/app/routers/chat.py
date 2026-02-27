"""
Chat Router
===========
API endpoints for conversation and message management.
Implements the core chat functionality between students and AI tutor.
"""

from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from typing import List, Optional, AsyncGenerator
import tempfile
import os
import logging
import re
import json

from app.models.conversation import ConversationCreate, ConversationResponse, ConversationUpdate
from app.models.message import MessageResponse, MessageCreate, ChatMessageRequest, ChatMessageResponse, AudioTranscriptionResponse
from app.database.conversations import ConversationsDatabase
from app.database.messages import MessagesDatabase
from app.database.profiles import ProfilesDatabase
from app.utils.security import decode_access_token
from app.services.chat_service import chat_service
from app.services.stt_service import stt_service
from app.services.tts_service import tts_service, SUPPORTED_LANGUAGES as TTS_SUPPORTED_LANGUAGES

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)

security = HTTPBearer()


async def get_current_profile_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Dependency to extract and validate profile ID from JWT token.
    
    This endpoint expects a profile-specific token (generated via POST /profiles/{id}/access),
    not the master user token.
    
    Args:
        credentials: HTTP Bearer token credentials
        
    Returns:
        Profile ID from token
        
    Raises:
        HTTPException: If token is invalid or profile doesn't exist
    """
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    # Check token type - should be profile_token
    token_type = payload.get("type")
    if token_type != "profile_token":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Profile token required for chat operations"
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


@router.post("/sessions", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conversation_data: ConversationCreate,
    profile_id: str = Depends(get_current_profile_id)
):
    """
    Start a new conversation thread.
    
    Args:
        conversation_data: Optional topic for the conversation
        profile_id: Profile ID from token
        
    Returns:
        Created ConversationResponse object
    """
    # Create the conversation
    conversation = await ConversationsDatabase.create_conversation(
        profile_id,
        conversation_data
    )
    
    return ConversationResponse(
        _id=str(conversation.id),
        profile_id=str(conversation.profile_id),
        title=conversation.title,
        subject_tag=conversation.subject_tag,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=0
    )


@router.get("/sessions", response_model=List[ConversationResponse], status_code=status.HTTP_200_OK)
async def list_conversations(
    limit: int = 20,
    offset: int = 0,
    profile_id: str = Depends(get_current_profile_id)
):
    """
    Get chat history list for the current profile.
    
    Returns conversations sorted by most recently updated first.
    
    Args:
        limit: Maximum number of conversations to return (default 20)
        offset: Number of conversations to skip (default 0)
        profile_id: Profile ID from token
        
    Returns:
        List of ConversationResponse objects
    """
    # Validate pagination parameters
    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit must be between 1 and 100"
        )
    
    if offset < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Offset must be non-negative"
        )
    
    conversations = await ConversationsDatabase.get_conversations_by_profile(
        profile_id,
        limit=limit,
        offset=offset
    )
    
    # Get message counts for each conversation
    conversation_responses = []
    for conv in conversations:
        message_count = await MessagesDatabase.count_messages_by_conversation(str(conv.id))
        
        conversation_responses.append(
            ConversationResponse(
                _id=str(conv.id),
                profile_id=str(conv.profile_id),
                title=conv.title,
                subject_tag=conv.subject_tag,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                message_count=message_count
            )
        )
    
    return conversation_responses


@router.get("/{conversation_id}/history", response_model=List[MessageResponse], status_code=status.HTTP_200_OK)
async def get_conversation_history(
    conversation_id: str,
    profile_id: str = Depends(get_current_profile_id)
):
    """
    Fetch full message history for a specific conversation.
    
    Returns messages in chronological order (oldest first).
    
    Args:
        conversation_id: Conversation's unique ID
        profile_id: Profile ID from token
        
    Returns:
        List of MessageResponse objects
        
    Raises:
        HTTPException: If conversation not found or doesn't belong to profile
    """
    # Verify conversation exists
    conversation = await ConversationsDatabase.get_conversation_by_id(conversation_id)
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Verify conversation belongs to current profile
    if str(conversation.profile_id) != profile_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this conversation"
        )
    
    # Get all messages
    messages = await MessagesDatabase.get_messages_by_conversation(conversation_id)
    
    return [
        MessageResponse(
            _id=str(msg.id),
            conversation_id=str(msg.conversation_id),
            profile_id=str(msg.profile_id),
            role=msg.role,
            content=msg.content,
            content_translated=msg.content_translated,
            audio_url=msg.audio_url,
            timestamp=msg.timestamp,
            rag_references=[str(ref) for ref in msg.rag_references],
            # Include TTS audio fields (will be None for user messages)
            audio_base64=msg.audio_base64,
            audio_format=msg.audio_format,
            audio_language=msg.audio_language,
            audio_language_name=msg.audio_language_name,
        )
        for msg in messages
    ]


@router.get("/{conversation_id}", response_model=ConversationResponse, status_code=status.HTTP_200_OK)
async def get_conversation(
    conversation_id: str,
    profile_id: str = Depends(get_current_profile_id)
):
    """
    Get details of a specific conversation.
    
    Args:
        conversation_id: Conversation's unique ID
        profile_id: Profile ID from token
        
    Returns:
        ConversationResponse object
        
    Raises:
        HTTPException: If conversation not found or doesn't belong to profile
    """
    conversation = await ConversationsDatabase.get_conversation_by_id(conversation_id)
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    if str(conversation.profile_id) != profile_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this conversation"
        )
    
    message_count = await MessagesDatabase.count_messages_by_conversation(conversation_id)
    
    return ConversationResponse(
        _id=str(conversation.id),
        profile_id=str(conversation.profile_id),
        title=conversation.title,
        subject_tag=conversation.subject_tag,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=message_count
    )


@router.put("/{conversation_id}", response_model=ConversationResponse, status_code=status.HTTP_200_OK)
async def update_conversation(
    conversation_id: str,
    conversation_update: ConversationUpdate,
    profile_id: str = Depends(get_current_profile_id)
):
    """
    Update conversation metadata (title, subject_tag).
    
    Args:
        conversation_id: Conversation's unique ID
        conversation_update: Fields to update
        profile_id: Profile ID from token
        
    Returns:
        Updated ConversationResponse object
        
    Raises:
        HTTPException: If conversation not found or access denied
    """
    # Verify conversation exists and belongs to profile
    existing_conversation = await ConversationsDatabase.get_conversation_by_id(conversation_id)
    
    if not existing_conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    if str(existing_conversation.profile_id) != profile_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this conversation"
        )
    
    # Update the conversation
    updated_conversation = await ConversationsDatabase.update_conversation(
        conversation_id,
        conversation_update
    )
    
    if not updated_conversation:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update conversation"
        )
    
    message_count = await MessagesDatabase.count_messages_by_conversation(conversation_id)
    
    return ConversationResponse(
        _id=str(updated_conversation.id),
        profile_id=str(updated_conversation.profile_id),
        title=updated_conversation.title,
        subject_tag=updated_conversation.subject_tag,
        created_at=updated_conversation.created_at,
        updated_at=updated_conversation.updated_at,
        message_count=message_count
    )


@router.delete("/{conversation_id}", status_code=status.HTTP_200_OK)
async def delete_conversation(
    conversation_id: str,
    profile_id: str = Depends(get_current_profile_id)
):
    """
    Delete a conversation and all its messages.
    
    Args:
        conversation_id: Conversation's unique ID
        profile_id: Profile ID from token
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If conversation not found or access denied
    """
    # Verify conversation exists and belongs to profile
    existing_conversation = await ConversationsDatabase.get_conversation_by_id(conversation_id)
    
    if not existing_conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    if str(existing_conversation.profile_id) != profile_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this conversation"
        )
    
    # Delete all messages first
    messages_deleted = await MessagesDatabase.delete_messages_by_conversation(conversation_id)
    
    # Delete the conversation
    success = await ConversationsDatabase.delete_conversation(conversation_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete conversation"
        )
    
    return {
        "status": "ok",
        "message": "Conversation deleted successfully",
        "messages_deleted": messages_deleted
    }


# =============================================================================
# Chat Message Endpoint - RAG-Enhanced AI Response
# =============================================================================

@router.post(
    "/{conversation_id}/message",
    status_code=status.HTTP_200_OK,
    summary="Send a message and get AI response",
    description="""
    Send a message in a conversation and receive an AI-generated response.
    
    This endpoint:
    1. Saves the user's message to the conversation
    2. Retrieves relevant knowledge from the RAG knowledge base
    3. Includes recent conversation history for context
    4. Generates a response using the Ollama LLM (Gemma model)
    5. Saves and returns the AI's response
    
    The AI tutor (DigiMasterJi) responds in the same language as the user's message
    and uses STEM curriculum content to provide accurate, educational responses.
    
    If stream=True, the response is sent as Server-Sent Events (SSE) with tokens
    streamed as they are generated.
    """
)
async def send_message(
    conversation_id: str,
    message: ChatMessageRequest,
    profile_id: str = Depends(get_current_profile_id)
):
    """
    Send a message and receive an AI tutor response.
    
    Args:
        conversation_id: The conversation's unique ID
        message: The user's message content
        profile_id: Profile ID from token
        
    Returns:
        ChatMessageResponse with the AI's response (or SSE stream if stream=True)
        
    Raises:
        HTTPException: 404 if conversation not found
        HTTPException: 403 if conversation doesn't belong to profile
        HTTPException: 500 if AI generation fails
    """
    # Verify conversation exists
    conversation = await ConversationsDatabase.get_conversation_by_id(conversation_id)
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Verify conversation belongs to current profile
    if str(conversation.profile_id) != profile_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this conversation"
        )
    
    # Fetch profile data for personalization
    profile = await ProfilesDatabase.get_profile_by_id(profile_id)
    profile_data = None
    if profile:
        profile_data = {
            "name": profile.name,
            "age": profile.age,
            "grade_level": profile.grade_level,
            "preferred_language": profile.preferred_language
        }
    
    # Step 1: Save the user's message
    user_message_data = MessageCreate(
        content=message.content,
        role="user"
    )
    
    user_msg = await MessagesDatabase.create_message(
        conversation_id=conversation_id,
        profile_id=profile_id,
        message_data=user_message_data
    )
    
    # If streaming is requested, return SSE stream
    if message.stream:
        return await _stream_response(
            conversation_id=conversation_id,
            profile_id=profile_id,
            message=message,
            conversation=conversation,
            profile=profile,
            profile_data=profile_data
        )
    
    # Non-streaming: Generate complete AI response using chat service
    ai_result = await chat_service.generate_response(
        conversation_id=conversation_id,
        user_message=message.content,
        subject=conversation.subject_tag,
        language=None,
        profile_data=profile_data,
        enable_web_search=message.enable_web_search
    )
    
    if not ai_result.get("success"):
        fallback_content = (
            "I'm sorry, I'm having trouble generating a response right now. "
            "Please try again in a moment. "
            "माफ़ कीजिए, मुझे अभी जवाब देने में परेशानी हो रही है।"
        )
        
        assistant_message_data = MessageCreate(
            content=fallback_content,
            role="assistant"
        )
        
        assistant_msg = await MessagesDatabase.create_message(
            conversation_id=conversation_id,
            profile_id=profile_id,
            message_data=assistant_message_data
        )
        
        await ConversationsDatabase.update_conversation_timestamp(conversation_id)
        
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI service temporarily unavailable: {ai_result.get('error', 'Unknown error')}"
        )
    
    # Save the AI's response
    assistant_message_data = MessageCreate(
        content=ai_result["response"],
        role="assistant"
    )
    
    assistant_msg = await MessagesDatabase.create_message(
        conversation_id=conversation_id,
        profile_id=profile_id,
        message_data=assistant_message_data
    )
    
    await ConversationsDatabase.update_conversation_timestamp(conversation_id)
    
    # Generate TTS audio if requested
    audio_base64, audio_format, audio_language, audio_language_name = await _generate_tts_audio(
        message=message,
        profile=profile,
        response_text=ai_result["response"],
        assistant_msg_id=str(assistant_msg.id)
    )
    
    return ChatMessageResponse(
        _id=str(assistant_msg.id),
        conversation_id=str(assistant_msg.conversation_id),
        role="assistant",
        content=assistant_msg.content,
        timestamp=assistant_msg.timestamp,
        audio_base64=audio_base64,
        audio_format=audio_format,
        audio_language=audio_language,
        audio_language_name=audio_language_name,
    )


async def _stream_response(
    conversation_id: str,
    profile_id: str,
    message: ChatMessageRequest,
    conversation,
    profile,
    profile_data: Optional[dict]
) -> StreamingResponse:
    """
    Generate and stream the AI response using Server-Sent Events (SSE).
    
    SSE Event Types:
    - token: Individual text tokens as they are generated
    - message_complete: Final message with metadata (id, timestamp)
    - diagram: Optional diagram data after response completes
    - error: Error information if generation fails
    """
    async def event_generator() -> AsyncGenerator[str, None]:
        full_response = ""
        assistant_msg = None
        
        try:
            # Stream tokens from the chat service
            async for token in chat_service.generate_response_stream(
                conversation_id=conversation_id,
                user_message=message.content,
                subject=conversation.subject_tag,
                language=None,
                profile_data=profile_data,
                enable_web_search=message.enable_web_search
            ):
                full_response += token
                # Send token as SSE event
                event_data = json.dumps({"token": token})
                yield f"data: {event_data}\n\n"
            
            # Save the complete response to database
            if full_response.strip():
                assistant_message_data = MessageCreate(
                    content=full_response.strip(),
                    role="assistant"
                )
                
                assistant_msg = await MessagesDatabase.create_message(
                    conversation_id=conversation_id,
                    profile_id=profile_id,
                    message_data=assistant_message_data
                )
                
                await ConversationsDatabase.update_conversation_timestamp(conversation_id)
                
                # Send completion event with message metadata immediately
                # TTS audio will be fetched separately via /messages/{id}/tts endpoint
                complete_data = json.dumps({
                    "type": "message_complete",
                    "message": {
                        "_id": str(assistant_msg.id),
                        "conversation_id": str(assistant_msg.conversation_id),
                        "role": "assistant",
                        "content": full_response.strip(),
                        "timestamp": assistant_msg.timestamp.isoformat(),
                        "audio_base64": None,
                        "audio_format": None,
                        "audio_language": None,
                        "audio_language_name": None,
                        "include_audio": message.include_audio  # Signal frontend to fetch TTS
                    }
                })
                yield f"data: {complete_data}\n\n"
            else:
                # Empty response - send error
                error_data = json.dumps({
                    "type": "error",
                    "error": "Empty response generated"
                })
                yield f"data: {error_data}\n\n"
                
        except Exception as e:
            logger.error(f"[Streaming] Error during streaming: {e}")
            import traceback
            traceback.print_exc()
            
            # Save fallback message
            fallback_content = (
                "I'm sorry, I'm having trouble generating a response right now. "
                "Please try again in a moment. "
                "माफ़ कीजिए, मुझे अभी जवाब देने में परेशानी हो रही है।"
            )
            
            try:
                assistant_message_data = MessageCreate(
                    content=fallback_content,
                    role="assistant"
                )
                
                assistant_msg = await MessagesDatabase.create_message(
                    conversation_id=conversation_id,
                    profile_id=profile_id,
                    message_data=assistant_message_data
                )
                
                await ConversationsDatabase.update_conversation_timestamp(conversation_id)
            except Exception as save_err:
                logger.error(f"[Streaming] Failed to save fallback message: {save_err}")
            
            
            error_data = json.dumps({
                "type": "error",
                "error": str(e)
            })
            yield f"data: {error_data}\n\n"
        
        # Send done event
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable buffering in nginx
        }
    )


async def _generate_tts_audio(
    message: ChatMessageRequest,
    profile,
    response_text: str,
    assistant_msg_id: str
) -> tuple:
    """Generate TTS audio for a response if requested."""
    audio_base64 = None
    audio_format = None
    audio_language = None
    audio_language_name = None
    
    if not message.include_audio:
        return audio_base64, audio_format, audio_language, audio_language_name
    
    logger.info(f"[TTS] Generating audio for response (slow={message.slow_audio})")
    
    # Determine TTS language from profile's preferred language
    tts_language = "en"
    if profile and profile.preferred_language:
        language_mapping = {
            "Hindi": "hi",
            "English": "en",
            "Bengali": "bn",
            "Tamil": "ta",
            "Telugu": "te",
            "Marathi": "mr",
            "Gujarati": "gu",
            "Kannada": "kn",
            "Malayalam": "ml",
            "Punjabi": "pa",
            "Urdu": "ur",
            "Nepali": "ne",
        }
        tts_language = language_mapping.get(profile.preferred_language, "en")
    
    if tts_language not in TTS_SUPPORTED_LANGUAGES:
        logger.warning(f"[TTS] Language '{tts_language}' not supported, falling back to English")
        tts_language = "en"
    
    logger.info(f"[TTS] Using language: {tts_language}")
    
    # Strip markdown formatting from text for clean TTS
    tts_text = response_text
    tts_text = re.sub(r'\*\*(.+?)\*\*', r'\1', tts_text)
    tts_text = re.sub(r'__(.+?)__', r'\1', tts_text)
    tts_text = re.sub(r'\*(.+?)\*', r'\1', tts_text)
    tts_text = re.sub(r'_(.+?)_', r'\1', tts_text)
    tts_text = re.sub(r'^\s*[\*\-\+]\s+', '', tts_text, flags=re.MULTILINE)
    tts_text = re.sub(r'^\s*\d+\.\s+', '', tts_text, flags=re.MULTILINE)
    tts_text = re.sub(r'^#+\s+', '', tts_text, flags=re.MULTILINE)
    tts_text = re.sub(r'`([^`]+)`', r'\1', tts_text)
    tts_text = re.sub(r'```[\s\S]*?```', '', tts_text)
    tts_text = re.sub(r'^>\s*', '', tts_text, flags=re.MULTILINE)
    tts_text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', tts_text)
    tts_text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', r'\1', tts_text)
    tts_text = re.sub(r'^[\-\*_]{3,}\s*$', '', tts_text, flags=re.MULTILINE)
    tts_text = re.sub(r'\n{3,}', '\n\n', tts_text)
    tts_text = tts_text.strip()
    
    logger.info(f"[TTS] Stripped markdown (original: {len(response_text)} chars, cleaned: {len(tts_text)} chars)")
    
    tts_result = tts_service.synthesize(
        text=tts_text,
        language=tts_language,
        slow=message.slow_audio
    )
    
    if tts_result.get("success"):
        audio_base64 = tts_result.get("audio_base64")
        audio_format = tts_result.get("format", "mp3")
        audio_language = tts_result.get("language")
        audio_language_name = tts_result.get("language_name")
        logger.info(f"[TTS] Audio generated: {tts_result.get('audio_size', 0)} bytes")
        
        # Save TTS audio to database
        await MessagesDatabase.update_message_tts_audio(
            message_id=assistant_msg_id,
            audio_base64=audio_base64,
            audio_format=audio_format,
            audio_language=audio_language,
            audio_language_name=audio_language_name
        )
    else:
        logger.error(f"[TTS] Failed to generate audio: {tts_result.get('error')}")
    
    return audio_base64, audio_format, audio_language, audio_language_name


# =============================================================================
# Text-to-Speech (TTS) Endpoint - Separate Audio Generation
# =============================================================================

@router.post(
    "/messages/{message_id}/tts",
    status_code=status.HTTP_200_OK,
    summary="Generate TTS audio for a message",
    description="""
    Generate text-to-speech audio for an existing message.
    
    This is a separate endpoint that allows the frontend to:
    1. First receive the text response quickly via streaming
    2. Then fetch TTS audio separately without blocking text display
    
    The audio is generated using the profile's preferred language.
    """
)
async def generate_message_tts(
    message_id: str,
    slow_audio: bool = False,
    profile_id: str = Depends(get_current_profile_id)
):
    """
    Generate TTS audio for a specific message.
    
    Args:
        message_id: The message ID to generate audio for
        slow_audio: Whether to generate slower-paced audio
        profile_id: Profile ID from token
        
    Returns:
        Audio data (base64 encoded) with format and language info
    """
    logger.info(f"[TTS] Generating audio for message: {message_id}")
    
    # Get the message
    message = await MessagesDatabase.get_message_by_id(message_id)
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    # Verify message belongs to profile's conversation
    conversation = await ConversationsDatabase.get_conversation_by_id(str(message.conversation_id))
    if not conversation or str(conversation.profile_id) != profile_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this message"
        )
    
    # Check if audio already exists for this message
    if message.audio_base64:
        logger.info(f"[TTS] Returning cached audio for message: {message_id}")
        return {
            "success": True,
            "message_id": message_id,
            "audio_base64": message.audio_base64,
            "audio_format": message.audio_format or "mp3",
            "audio_language": message.audio_language,
            "audio_language_name": message.audio_language_name,
            "cached": True
        }
    
    # Get profile for language preference
    profile = await ProfilesDatabase.get_profile_by_id(profile_id)
    
    # Determine TTS language
    tts_language = "en"
    if profile and profile.preferred_language:
        language_mapping = {
            "Hindi": "hi",
            "English": "en",
            "Bengali": "bn",
            "Tamil": "ta",
            "Telugu": "te",
            "Marathi": "mr",
            "Gujarati": "gu",
            "Kannada": "kn",
            "Malayalam": "ml",
            "Punjabi": "pa",
            "Urdu": "ur",
            "Nepali": "ne",
        }
        tts_language = language_mapping.get(profile.preferred_language, "en")
    
    if tts_language not in TTS_SUPPORTED_LANGUAGES:
        logger.warning(f"[TTS] Language '{tts_language}' not supported, falling back to English")
        tts_language = "en"
    
    # Strip markdown formatting from text
    tts_text = message.content
    tts_text = re.sub(r'\*\*(.+?)\*\*', r'\1', tts_text)
    tts_text = re.sub(r'__(.+?)__', r'\1', tts_text)
    tts_text = re.sub(r'\*(.+?)\*', r'\1', tts_text)
    tts_text = re.sub(r'_(.+?)_', r'\1', tts_text)
    tts_text = re.sub(r'^\s*[\*\-\+]\s+', '', tts_text, flags=re.MULTILINE)
    tts_text = re.sub(r'^\s*\d+\.\s+', '', tts_text, flags=re.MULTILINE)
    tts_text = re.sub(r'^#+\s+', '', tts_text, flags=re.MULTILINE)
    tts_text = re.sub(r'`([^`]+)`', r'\1', tts_text)
    tts_text = re.sub(r'```[\s\S]*?```', '', tts_text)
    tts_text = re.sub(r'^>\s*', '', tts_text, flags=re.MULTILINE)
    tts_text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', tts_text)
    tts_text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', r'\1', tts_text)
    tts_text = re.sub(r'^[\-\*_]{3,}\s*$', '', tts_text, flags=re.MULTILINE)
    tts_text = re.sub(r'\n{3,}', '\n\n', tts_text)
    tts_text = tts_text.strip()
    
    # Generate TTS
    tts_result = tts_service.synthesize(
        text=tts_text,
        language=tts_language,
        slow=slow_audio
    )
    
    if not tts_result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"TTS generation failed: {tts_result.get('error', 'Unknown error')}"
        )
    
    audio_base64 = tts_result.get("audio_base64")
    audio_format = tts_result.get("format", "mp3")
    audio_language = tts_result.get("language")
    audio_language_name = tts_result.get("language_name")
    
    # Save to database for caching
    await MessagesDatabase.update_message_tts_audio(
        message_id=message_id,
        audio_base64=audio_base64,
        audio_format=audio_format,
        audio_language=audio_language,
        audio_language_name=audio_language_name
    )
    
    logger.info(f"[TTS] Audio generated successfully for message: {message_id}")
    
    return {
        "success": True,
        "message_id": message_id,
        "audio_base64": audio_base64,
        "audio_format": audio_format,
        "audio_language": audio_language,
        "audio_language_name": audio_language_name,
        "cached": False
    }


# =============================================================================
# Audio Transcription Endpoint - Speech-to-Text (STT)
# =============================================================================

# Supported audio formats
SUPPORTED_AUDIO_FORMATS = {
    "audio/wav", "audio/wave", "audio/x-wav",
    "audio/mpeg", "audio/mp3",
    "audio/webm", "audio/ogg",
    "audio/flac", "audio/x-flac",
    "audio/m4a", "audio/mp4"
}

# Maximum file size (10 MB)
MAX_AUDIO_SIZE = 10 * 1024 * 1024


@router.post(
    "/{conversation_id}/audio",
    response_model=AudioTranscriptionResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload voice query for transcription",
    description="""
    Upload an audio file to be transcribed to text using Speech-to-Text (STT).
    
    This endpoint:
    1. Receives an audio file (WAV, MP3, WebM, OGG, FLAC, M4A supported)
    2. Saves the file temporarily
    3. Transcribes the audio using configured STT provider (local Whisper or Deepgram)
    4. Deletes the temporary file
    5. Returns the transcribed text
    
    The transcribed text can then be sent to the /chat/{id}/message endpoint
    to get an AI response.
    
    Supports multiple Indian languages including Hindi, English, Tamil, Telugu, etc.
    Language handling is controlled by STT_LANGUAGE_MODE environment variable:
    - 'profile': Uses profile's preferred_language (default)
    - 'auto': Auto-detect language from audio
    """
)
async def transcribe_audio(
    conversation_id: str,
    file: UploadFile = File(..., description="Audio file to transcribe"),
    language: Optional[str] = Form(None, description="Language code (e.g., 'hi' for Hindi). If not provided, behavior depends on STT_LANGUAGE_MODE setting."),
    profile_id: str = Depends(get_current_profile_id)
):
    """
    Upload and transcribe an audio file to text.
    
    Args:
        conversation_id: The conversation's unique ID (for context/logging)
        file: The audio file to transcribe
        language: Optional language code for transcription
        profile_id: Profile ID from token
        
    Returns:
        AudioTranscriptionResponse with the transcribed text
        
    Raises:
        HTTPException: 404 if conversation not found
        HTTPException: 403 if conversation doesn't belong to profile
        HTTPException: 400 if file format is unsupported or file is too large
        HTTPException: 500 if transcription fails
    """
    logger.info(f"[STT] Audio transcription request for conversation: {conversation_id}")
    
    # Determine transcription language based on STT_LANGUAGE_MODE setting
    transcription_language = language
    if not transcription_language and stt_service.should_use_profile_language():
        # STT_LANGUAGE_MODE is 'profile' - use profile's preferred language
        profile = await ProfilesDatabase.get_profile_by_id(profile_id)
        if profile and profile.preferred_language:
            transcription_language = profile.preferred_language
            logger.info(f"[STT] Using profile's preferred language: {transcription_language}")
    # If STT_LANGUAGE_MODE is 'auto', transcription_language stays None for auto-detect
    
    
    # Verify conversation exists
    conversation = await ConversationsDatabase.get_conversation_by_id(conversation_id)
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Verify conversation belongs to current profile
    if str(conversation.profile_id) != profile_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this conversation"
        )
    
    # Validate file type
    content_type = file.content_type or ""
    if content_type not in SUPPORTED_AUDIO_FORMATS:
        # Also check by file extension as fallback
        filename = file.filename or ""
        valid_extensions = (".wav", ".mp3", ".webm", ".ogg", ".flac", ".m4a", ".mp4")
        if not filename.lower().endswith(valid_extensions):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported audio format: {content_type}. Supported formats: WAV, MP3, WebM, OGG, FLAC, M4A"
            )
    
    # Read file content
    try:
        audio_bytes = await file.read()
    except Exception as e:
        logger.error(f"[STT] Error reading audio file: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error reading audio file: {str(e)}"
        )
    
    # Validate file size
    if len(audio_bytes) > MAX_AUDIO_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Audio file too large. Maximum size is {MAX_AUDIO_SIZE // (1024*1024)} MB"
        )
    
    if len(audio_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty audio file uploaded"
        )
    
    logger.info(f"[STT] Received audio file: {file.filename}, size: {len(audio_bytes)} bytes, type: {content_type}")
    
    # Save to temporary file
    temp_path = None
    try:
        # Determine file extension
        filename = file.filename or "audio.wav"
        ext = os.path.splitext(filename)[1] or ".wav"
        
        # Create temp file
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as temp_file:
            temp_path = temp_file.name
            temp_file.write(audio_bytes)
        
        logger.info(f"[STT] Saved audio to temp file: {temp_path}")
        
        # Transcribe using STT service (async for better performance with Deepgram)
        provider_info = f"provider={stt_service.provider}"
        logger.info(f"[STT] Starting transcription ({provider_info}, language={transcription_language or 'auto-detect'})...")
        
        result = await stt_service.transcribe_file_async(
            file_path=temp_path,
            language=transcription_language,
            task="transcribe"
        )
        
        if not result.get("success"):
            error_msg = result.get("error", "Unknown transcription error")
            logger.error(f"[STT] Transcription failed: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Transcription failed: {error_msg}"
            )
        
        transcribed_text = result.get("text", "").strip()
        detected_language = result.get("language", transcription_language)
        stt_provider = result.get("provider", stt_service.provider)
        
        logger.info(f"[STT] Transcription successful via {stt_provider}: '{transcribed_text[:50]}...' (language: {detected_language})")
        
        # Map language code to name
        from app.services.stt_service import SUPPORTED_LANGUAGES
        language_name = SUPPORTED_LANGUAGES.get(detected_language, detected_language)
        
        return AudioTranscriptionResponse(
            success=True,
            transcribed_text=transcribed_text,
            language=detected_language,
            language_name=language_name,
            duration_seconds=None  # Could be calculated if needed
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"[STT] Unexpected error during transcription: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transcription error: {str(e)}"
        )
    finally:
        # Always clean up temp file
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
                logger.info(f"[STT] Cleaned up temp file: {temp_path}")
            except Exception as e:
                logger.warning(f"[STT] Failed to delete temp file {temp_path}: {e}")


# =============================================================================
# Offline Chat Endpoints
# =============================================================================

@router.get("/offline/status", status_code=status.HTTP_200_OK)
async def check_offline_status(
    profile_id: str = Depends(get_current_profile_id)
):
    """
    Check if offline chat mode is available.
    
    Returns:
        Dictionary with offline availability status
    """
    is_available = await chat_service.check_offline_availability()
    
    from app.services.offline_llm_service import offline_llm_service
    availability = await offline_llm_service.check_availability()
    
    return {
        "offline_available": is_available,
        "offline_model": availability.get("offline_model"),
        "status": availability.get("status"),
        "message": "Offline chat is available" if is_available else "Offline model not installed. Run: ollama pull gemma3:1b"
    }


@router.post(
    "/{conversation_id}/message/offline",
    status_code=status.HTTP_200_OK,
    summary="Send a message using offline mode",
    description="""
    Send a message and receive a response using the local offline model.
    
    Offline mode features:
    - Uses smaller Gemma3 270M parameter model
    - All responses are in English
    - No RAG or web search capabilities
    - Works without internet connection
    """
)
async def send_message_offline(
    conversation_id: str,
    message: ChatMessageRequest,
    profile_id: str = Depends(get_current_profile_id)
):
    """
    Send a message using offline mode (local model).
    
    Args:
        conversation_id: The conversation's unique ID
        message: The user's message content
        profile_id: Profile ID from token
        
    Returns:
        ChatMessageResponse with the AI's response in offline mode
    """
    # Check offline availability
    is_available = await chat_service.check_offline_availability()
    if not is_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Offline mode not available. Please install the offline model: ollama pull gemma3:1b"
        )
    
    # Verify conversation exists
    conversation = await ConversationsDatabase.get_conversation_by_id(conversation_id)
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    if str(conversation.profile_id) != profile_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this conversation"
        )
    
    # Save user message
    user_message_data = MessageCreate(
        content=message.content,
        role="user"
    )
    
    user_msg = await MessagesDatabase.create_message(
        conversation_id=conversation_id,
        profile_id=profile_id,
        message_data=user_message_data
    )
    
    # Check for streaming request
    if message.stream:
        return await _stream_offline_response(
            conversation_id=conversation_id,
            profile_id=profile_id,
            message=message
        )
    
    # Generate offline response
    ai_result = await chat_service.generate_offline_response(
        conversation_id=conversation_id,
        user_message=message.content
    )
    
    if not ai_result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Offline generation failed: {ai_result.get('error', 'Unknown error')}"
        )
    
    # Save the AI's response
    assistant_message_data = MessageCreate(
        content=ai_result["response"],
        role="assistant"
    )
    
    assistant_msg = await MessagesDatabase.create_message(
        conversation_id=conversation_id,
        profile_id=profile_id,
        message_data=assistant_message_data
    )
    
    await ConversationsDatabase.update_conversation_timestamp(conversation_id)
    
    return ChatMessageResponse(
        _id=str(assistant_msg.id),
        conversation_id=str(assistant_msg.conversation_id),
        role="assistant",
        content=assistant_msg.content,
        timestamp=assistant_msg.timestamp,
        offline_mode=True
    )


async def _stream_offline_response(
    conversation_id: str,
    profile_id: str,
    message: ChatMessageRequest
) -> StreamingResponse:
    """
    Generate and stream offline AI response using SSE.
    """
    async def event_generator() -> AsyncGenerator[str, None]:
        full_response = ""
        
        try:
            # Stream tokens from offline service
            async for token in chat_service.generate_offline_response_stream(
                conversation_id=conversation_id,
                user_message=message.content
            ):
                full_response += token
                event_data = json.dumps({"token": token})
                yield f"data: {event_data}\n\n"
            
            # Save the complete response
            if full_response.strip():
                assistant_message_data = MessageCreate(
                    content=full_response.strip(),
                    role="assistant"
                )
                
                assistant_msg = await MessagesDatabase.create_message(
                    conversation_id=conversation_id,
                    profile_id=profile_id,
                    message_data=assistant_message_data
                )
                
                await ConversationsDatabase.update_conversation_timestamp(conversation_id)
                
                # Send completion event
                complete_data = json.dumps({
                    "type": "message_complete",
                    "message": {
                        "_id": str(assistant_msg.id),
                        "conversation_id": str(assistant_msg.conversation_id),
                        "role": "assistant",
                        "content": full_response.strip(),
                        "timestamp": assistant_msg.timestamp.isoformat(),
                        "offline_mode": True
                    }
                })
                yield f"data: {complete_data}\n\n"
            
        except Exception as e:
            logger.error(f"[OFFLINE STREAM] Error: {e}")
            error_data = json.dumps({"type": "error", "error": str(e)})
            yield f"data: {error_data}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
