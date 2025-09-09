from fastapi import APIRouter, HTTPException, status
from uuid import UUID
from typing import List
import logging

from src.database.core import DbSession, CheckpointerDep
from src.auth.service import CurrentUser
from . import models, service

router = APIRouter(
    prefix="/conversations",
    tags=["Conversations"]
)

@router.get("/", response_model=List[models.ConversationListItem])
def list_user_conversations(
    db: DbSession,
    current_user: CurrentUser
):
    """
    Returns the list of conversations for the authenticated user from PostgreSQL,
    sorted by the most recently updated.
    """
    user_id = current_user.get_uuid()
    return service.get_user_conversations_list(db, user_id)

@router.get("/{conversation_id}", response_model=models.ConversationHistoryResponse)
def get_conversation_details(
    conversation_id: UUID,
    db: DbSession,
    checkpointer: CheckpointerDep,
    current_user: CurrentUser
):
    """
    Returns the detailed message history for a specific conversation from PostgreSQL.
    Ensures the user has permission to view the conversation.
    """
    user_id = current_user.get_uuid()
    try:
        return service.get_conversation_history(db, checkpointer, user_id, conversation_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logging.error(f"An unexpected error occurred while fetching conversation {conversation_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An internal error occurred.")

@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: UUID,
    db: DbSession,
    current_user: CurrentUser
):
    """
    Deletes a specific conversation from PostgreSQL.
    Ensures the user has permission to delete the conversation.
    Also cleans up associated data from Redis checkpointer.
    """
    user_id = current_user.get_uuid()
    try:
        service.delete_conversation(db, user_id, conversation_id)
        logging.info(f"Successfully deleted conversation {conversation_id} for user {user_id}")
        return None  # 204 No Content response
    except service.ConversationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Conversation with id {conversation_id} not found"
        )
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="You don't have permission to delete this conversation"
        )
    except Exception as e:
        logging.error(f"Error deleting conversation {conversation_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="An error occurred while deleting the conversation"
        )