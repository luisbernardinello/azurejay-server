from fastapi import APIRouter, HTTPException, status, Body
from uuid import UUID
from typing import List
import logging

from ..database.core import DbSession
from ..auth.service import CurrentUser
from . import models, service
from ..exceptions import ConversationNotFoundError

router = APIRouter(
    prefix="/conversations",
    tags=["Conversations"]
)

@router.get("/", response_model=List[models.ConversationListItem])
def list_user_conversations(db: DbSession, current_user: CurrentUser):
    """Retorna a lista de conversas do usuário, ordenada pela mais recente."""
    return service.get_user_conversations_list(db, current_user.get_uuid())

@router.get("/{conversation_id}", response_model=models.ConversationHistoryResponse)
def get_conversation_details(
    conversation_id: UUID,
    db: DbSession,
    current_user: CurrentUser
):
    """Retorna o histórico detalhado de mensagens de uma conversa específica."""
    try:
        return service.get_conversation_history(db, current_user.get_uuid(), conversation_id)
    except ConversationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logging.error(f"Erro ao buscar conversa {conversation_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@router.post("/", response_model=models.NewConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    request: models.NewConversationRequest,
    db: DbSession,
    current_user: CurrentUser
):
    """Cria uma nova conversa com a primeira mensagem do usuário."""
    try:
        return await service.create_new_conversation(db, current_user.get_uuid(), request)
    except Exception as e:
        logging.error(f"Erro ao criar nova conversa: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha ao criar a conversa.")

@router.post("/{conversation_id}/chat", response_model=models.ChatResponse)
async def chat_in_conversation(
    conversation_id: UUID,
    request: models.ChatRequest,
    db: DbSession,
    current_user: CurrentUser
):
    """Envia uma nova mensagem para uma conversa existente."""
    try:
        service.get_conversation_history(db, current_user.get_uuid(), conversation_id)
        
        response_content = await service.process_new_message(
            db=db,
            user_id=current_user.get_uuid(),
            conversation_id=conversation_id,
            user_input=request.content
        )
        return models.ChatResponse(response=response_content)
    except ConversationNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada.")
    except Exception as e:
        logging.error(f"Erro ao processar mensagem na conversa {conversation_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha ao processar a mensagem.")


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