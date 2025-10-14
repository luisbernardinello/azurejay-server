import logging
import traceback
from uuid import UUID, uuid4
from datetime import datetime
from typing import List
from sqlalchemy.orm import Session, selectinload

from . import models
from ..entities.conversation import Conversation
from ..entities.message import Message, MessageRole
from ..exceptions import ConversationNotFoundError

from ..agent.grammar_pipe import create_preprocessing_graph
from ..agent.afm_executor import run_afm_cycle
from ..database.core import store_instance as store
from ..users.service import get_user_profile
from langdetect import detect, LangDetectException

preprocessing_graph = create_preprocessing_graph()


def get_user_conversations_list(db: Session, user_id: UUID) -> List[models.ConversationListItem]:
    """Busca a lista de conversas do usuário."""
    conversations = (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    return [
        models.ConversationListItem(
            id=conv.id, title=conv.title, updated_at=conv.updated_at
        )
        for conv in conversations
    ]

def get_conversation_history(db: Session, user_id: UUID, conversation_id: UUID) -> models.ConversationHistoryResponse:
    """Busca o histórico completo de uma conversa com suas mensagens e correções."""
    conversation = (
        db.query(Conversation)
        .options(
            selectinload(Conversation.messages).options(
                selectinload(Message.correction)
            )
        )
        .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
        .first()
    )

    if not conversation:
        raise ConversationNotFoundError(conversation_id)

    message_details = []
    for msg in conversation.messages:
        correction_detail = None
        if msg.correction:
            correction_detail = models.GrammarCorrectionDetail(
                original_text=msg.correction.original_text,
                corrected_text=msg.correction.corrected_text,
                explanation=msg.correction.explanation,
                improvement=msg.correction.improvement,
            )
        message_details.append(models.MessageDetail(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            correction=correction_detail
        ))
    
    return models.ConversationHistoryResponse(
        id=conversation.id,
        title=conversation.title,
        messages=message_details
    )

async def process_new_message(
    db: Session,
    user_id: UUID,
    conversation_id: UUID,
    user_input: str,
) -> str:
    """
    Função central que processa uma nova mensagem de usuário, seja em uma conversa nova ou existente.
    """

    try:
        lang = detect(user_input)
        if lang != 'en':
            ai_response = "I'm sorry, I can only chat in English. Could you please rephrase your message?"
            
            # Salva a mensagem do usuário
            user_message = Message(
                conversation_id=conversation_id,
                role=MessageRole.HUMAN,
                content=user_input
            )
            db.add(user_message)

            # Salva a resposta da IA
            ai_message = Message(
                conversation_id=conversation_id,
                role=MessageRole.AI,
                content=ai_response
            )
            db.add(ai_message)
            db.commit()
            
            return ai_response
    except LangDetectException:
        logging.warning("Language detection failed for input. Proceeding as if it is English.")

    # Salva a mensagem do usuário no banco de dados primeiro
    user_message = Message(
        conversation_id=conversation_id,
        role=MessageRole.HUMAN,
        content=user_input
    )
    db.add(user_message)
    db.commit()
    db.refresh(user_message)
    
    # Carrega o histórico da conversa e o perfil do usuário
    history = get_conversation_history(db, user_id, conversation_id)
    conversation_history_list = [{"role": msg.role, "content": msg.content} for msg in history.messages]
    
    # Carrega o perfil do Redis
    profile_namespace = ("profile", str(user_id))
    existing_profile = store.search(profile_namespace)
    user_profile_str = "Nenhum perfil salvo ainda."
    if existing_profile:
        user_profile_str = str(existing_profile[0].value)

    # Executa o pipeline de préprocessamento
    pipeline_state = preprocessing_graph.invoke({"user_input": user_input})
    syntactic_analysis = pipeline_state.get("syntactic_analysis", "")
    semantic_analysis = pipeline_state.get("semantic_analysis", "")

    # Executa o agente AFM
    final_answer = await run_afm_cycle(
        user_input=user_input,
        conversation_history=conversation_history_list,
        user_profile=user_profile_str,
        syntactic_analysis=syntactic_analysis,
        semantic_analysis=semantic_analysis,
        store=store,
        user_id=str(user_id),
        db_session=db,
        conversation_id=str(conversation_id),
    )
    
    # Salva a resposta do agente no banco de dados
    ai_message = Message(
        conversation_id=conversation_id,
        role=MessageRole.AI,
        content=final_answer
    )
    db.add(ai_message)
    
    # Atualiza o timestamp da conversa
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if conversation:
        conversation.updated_at = datetime.utcnow()
        
    db.commit()
    
    return final_answer


async def create_new_conversation(db: Session, user_id: UUID, request: models.NewConversationRequest) -> models.NewConversationResponse:
    """Cria uma nova conversa e processa a primeira mensagem."""
    title = request.content[:60].strip() + ("..." if len(request.content) > 60 else "")
    
    # Cria a nova conversa no DB
    new_conversation = Conversation(
        user_id=user_id,
        title=title,
    )
    db.add(new_conversation)
    db.commit()
    db.refresh(new_conversation)
    
    # Processa a primeira mensagem usando a função central
    final_answer = await process_new_message(
        db=db,
        user_id=user_id,
        conversation_id=new_conversation.id,
        user_input=request.content
    )
    
    return models.NewConversationResponse(
        response=final_answer,
        conversation_id=new_conversation.id,
        title=title
    )

def delete_conversation(
    db: Session,
    user_id: UUID,
    conversation_id: UUID
) -> None:
    """
    Deletes a conversation from PostgreSQL and cleans up associated Redis data.
    
    Args:
        db: Database session
        user_id: ID of the user making the request
        conversation_id: ID of the conversation to delete
        
    Raises:
        ConversationNotFoundError: If conversation doesn't exist
        PermissionError: If user doesn't own the conversation
    """
    try:
        conversation = (
            db.query(Conversation)
            .filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id
            )
            .first()
        )
        
        if not conversation:
            existing_conversation = (
                db.query(Conversation)
                .filter(Conversation.id == conversation_id)
                .first()
            )
            
            if existing_conversation:
                raise PermissionError("You don't have permission to delete this conversation")
            else:
                raise ConversationNotFoundError(conversation_id)
        
        db.delete(conversation)
        db.commit()
        
        logging.info(f"Successfully deleted conversation {conversation_id} for user {user_id}")
        
    except (ConversationNotFoundError, PermissionError):
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logging.error(f"Error deleting conversation {conversation_id}: {e}")
        logging.error(traceback.format_exc())
        raise