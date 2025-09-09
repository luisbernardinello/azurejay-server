from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional

class NewAudioConversationResponse(BaseModel):
    """
    Response model for creating a new conversation via audio.
    """
    conversation_id: UUID = Field(
        ...,
        description="The ID of the newly created conversation for frontend redirection."
    )
    title: str = Field(
        ...,
        description="The title of the new conversation (derived from transcribed message)."
    )

class AudioChatResponse(BaseModel):
    """
    Response model for continuing an audio conversation.
    """
    success: bool = Field(
        default=True,
        description="Indicates if the audio processing was successful."
    )