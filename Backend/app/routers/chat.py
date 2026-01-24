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
            audio_language_name=msg.audio_language_name
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
        profile_data=profile_data
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
        audio_language_name=audio_language_name
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
                profile_data=profile_data
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
                
                # Generate TTS audio if requested (after streaming completes)
                audio_base64 = None
                audio_format = None
                audio_language = None
                audio_language_name = None
                
                if message.include_audio:
                    audio_base64, audio_format, audio_language, audio_language_name = await _generate_tts_audio(
                        message=message,
                        profile=profile,
                        response_text=full_response.strip(),
                        assistant_msg_id=str(assistant_msg.id)
                    )
                
                # Send completion event with message metadata
                complete_data = json.dumps({
                    "type": "message_complete",
                    "message": {
                        "_id": str(assistant_msg.id),
                        "conversation_id": str(assistant_msg.conversation_id),
                        "role": "assistant",
                        "content": full_response.strip(),
                        "timestamp": assistant_msg.timestamp.isoformat(),
                        "audio_base64": audio_base64,
                        "audio_format": audio_format,
                        "audio_language": audio_language,
                        "audio_language_name": audio_language_name
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
