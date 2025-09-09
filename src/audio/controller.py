import os
import tempfile
import logging
from uuid import UUID
from fastapi import APIRouter, HTTPException, status, UploadFile, File, Path
from fastapi.responses import StreamingResponse, Response

from src.database.core import DbSession
from src.auth.service import CurrentUser
from src.agent import service as agent_service
from src.agent import models as agent_models
from src.conversations import service as conversation_service
from src.conversations import models as conversation_models
from src.conversations.service import add_message_to_conversation
from src.tts.service import convert_text_to_speech
from .service import convert_audio_to_text
from . import models

router = APIRouter(
    prefix="/audio",
    tags=["Audio"]
)

@router.post("/new", status_code=status.HTTP_201_CREATED)
async def create_new_audio_conversation(
    current_user: CurrentUser = None,
    db: DbSession = None,
    file: UploadFile = File(..., description="Audio file for the first message (m4a, wav, mp3, etc.)")
):
    """
    Creates a new conversation with the user's first audio message.
    Returns audio response with conversation metadata in headers.
    """
    user_id = current_user.get_uuid()
    temp_file_path = None
    
    try:
        allowed_types = ["audio/mpeg", "audio/mp4", "audio/wav", "audio/x-m4a", "audio/m4a"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type: {file.content_type}. Supported types: {allowed_types}"
            )
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file.filename.split('.')[-1]}") as temp_file:
            temp_file_path = temp_file.name
            content = await file.read()
            temp_file.write(content)
                
        # Convert audio to text
        transcribed_text = await convert_audio_to_text(temp_file_path)
        if not transcribed_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to transcribe audio. Please ensure the audio is clear and in a supported language."
            )
                
        new_conversation_request = conversation_models.NewConversationRequest(
            content=transcribed_text
        )
        
        conversation_response = await conversation_service.create_new_conversation(
            db=db,
            user_id=user_id,
            request=new_conversation_request
        )
        
        logging.info(f"Created new conversation: {conversation_response.conversation_id}")
        
        # Convert AI response to speech
        audio_content = convert_text_to_speech(
            message=conversation_response.response,
            voice="rachel",
            stability=0.6,
            similarity_boost=0.8
        )
        
        if not audio_content:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to convert response to speech"
            )
                
        # Return audio with conversation data in headers
        return Response(
            content=audio_content,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "attachment; filename=response.mp3",
                "X-Conversation-ID": str(conversation_response.conversation_id),
                "X-Conversation-Title": conversation_response.title,
                "Access-Control-Expose-Headers": "Content-Disposition,X-Conversation-ID,X-Conversation-Title"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error creating new audio conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred creating the audio conversation: {str(e)}"
        )
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
                logging.info(f"Cleaned up temporary file: {temp_file_path}")
            except Exception as e:
                logging.warning(f"Failed to clean up temporary file {temp_file_path}: {e}")

@router.post("/chat/{conversation_id}")
async def continue_audio_conversation(
    conversation_id: UUID = Path(..., description="The ID of the existing conversation"),
    current_user: CurrentUser = None,
    db: DbSession = None,
    file: UploadFile = File(..., description="Audio file (m4a, wav, mp3, etc.)")
):
    """
    Continues an existing conversation with audio input.
    Returns only the audio response.
    """
    user_id = current_user.get_uuid()
    temp_file_path = None
    
    try:
        await agent_service.validate_conversation_access(db, user_id, conversation_id)
        
        allowed_types = ["audio/mpeg", "audio/mp4", "audio/wav", "audio/x-m4a", "audio/m4a"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type: {file.content_type}. Supported types: {allowed_types}"
            )
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file.filename.split('.')[-1]}") as temp_file:
            temp_file_path = temp_file.name
            content = await file.read()
            temp_file.write(content)
        
        logging.info(f"Saved audio message temporarily: {temp_file_path}")
        
        # Convert audio to text
        transcribed_text = await convert_audio_to_text(temp_file_path)
        if not transcribed_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to transcribe audio. Please ensure the audio is clear and in a supported language."
            )
        
        logging.info(f"Transcribed message: {transcribed_text}")
        
        # Create agent request (reusing existing agent service)
        agent_request = agent_models.AgentRequest(
            content=transcribed_text,
            conversation_id=conversation_id
        )
        
        def add_message_wrapper(db, user_id, conversation_id, human_message, ai_response, improvement_analysis=None):
            return add_message_to_conversation(
                db=db,
                user_id=user_id,
                conversation_id=conversation_id,
                human_message=human_message,
                ai_response=ai_response,
                improvement_analysis=improvement_analysis
            )
        
        # Get AI response using existing agent service
        agent_response = await agent_service.chat_with_agent(
            db=db,
            user_id=user_id,
            request=agent_request,
            add_message_func=add_message_wrapper
        )
        
        logging.info(f"AI response: {agent_response.response}")
        
        # Convert AI response to speech
        audio_content = convert_text_to_speech(
            message=agent_response.response,
            voice="rachel",
            stability=0.6,
            similarity_boost=0.8
        )
        
        if not audio_content:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to convert response to speech"
            )
                
        # Return only audio
        return Response(
            content=audio_content,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "attachment; filename=response.mp3",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error continuing audio conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred processing the audio: {str(e)}"
        )
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
                logging.info(f"Cleaned up temporary file: {temp_file_path}")
            except Exception as e:
                logging.warning(f"Failed to clean up temporary file {temp_file_path}: {e}")