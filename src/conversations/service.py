import json
import logging
from uuid import UUID, uuid4
from datetime import datetime
from typing import List
import traceback
from sqlalchemy.orm.attributes import flag_modified

from sqlalchemy.orm import Session
from langchain_core.messages import HumanMessage, AIMessage

from . import models
from ..entities.conversation import Conversation
from ..agent.service import get_agent_graph
from ..exceptions import ConversationNotFoundError


def get_user_conversations_list(
    db: Session,
    user_id: UUID
) -> List[models.ConversationListItem]:
    """
    Gets a user's conversation list from PostgreSQL.
    Returns a list sorted by the most recently updated.
    """
    try:
        conversations = (
            db.query(Conversation)
            .filter(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .all()
        )
        
        return [
            models.ConversationListItem(
                id=conv.id,
                title=conv.title,
                updated_at=conv.updated_at
            )
            for conv in conversations
        ]
    except Exception as e:
        logging.error(f"Error fetching conversation list for user {user_id}: {e}")
        return []


def get_conversation_history(
    db: Session,
    checkpointer,
    user_id: UUID,
    conversation_id: UUID
) -> models.ConversationHistoryResponse:
    """
    Retrieves the full message history for a specific conversation from PostgreSQL.
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
            raise ConversationNotFoundError(conversation_id)
        
        messages = []
        for msg_data in conversation.messages:
            messages.append(models.MessageDetail(
                role=msg_data['role'],
                content=msg_data['content'],
                analysis=msg_data.get('analysis')
            ))
        
        return models.ConversationHistoryResponse(
            id=conversation.id,
            title=conversation.title,
            messages=messages
        )
        
    except ConversationNotFoundError:
        raise
    except Exception as e:
        logging.error(f"Error fetching conversation history for {conversation_id}: {e}")
        raise


async def create_new_conversation(
    db: Session,
    user_id: UUID,
    request: models.NewConversationRequest,
) -> models.NewConversationResponse:
    """
    Creates a new conversation with the user's first message in PostgreSQL.
    Uses LangGraph only for agent processing, stores conversation in DB.
    """
    conversation_id = uuid4()
    
    title = request.content[:60].strip()
    if len(request.content) > 60:
        title += "..."
    
    config = {
        "configurable": {
            "thread_id": str(conversation_id),
            "user_id": str(user_id),
        }
    }

    app = get_agent_graph()
    input_messages = [HumanMessage(content=request.content)]
    final_response = None
    improvement_analysis = None

    try:
        # Collect all messages during streaming
        all_messages = []
        
        # Asynchronously stream the graph's execution
        async for chunk in app.astream(
            {"messages": input_messages}, config, stream_mode="values"
        ):
            if "messages" in chunk and chunk["messages"]:
                all_messages = chunk["messages"]
                
                last_message = chunk["messages"][-1]
                

                if (isinstance(last_message, AIMessage) and 
                    (not hasattr(last_message, 'name') or last_message.name is None) and 
                    last_message.content.strip()):
                    final_response = last_message
                    
                    if hasattr(last_message, 'additional_kwargs') and 'improvement' in last_message.additional_kwargs:
                        improvement_analysis = {"improvement": last_message.additional_kwargs['improvement']}
                    
                    break
                
                elif isinstance(last_message, AIMessage) and last_message.content.strip():
                    if not (hasattr(last_message, 'name') and 
                           last_message.name in ['supervisor', 'correction', 'researcher', 'enhancer', 'validator']):
                        final_response = last_message
        
        if final_response is None and all_messages:
            for msg in reversed(all_messages):
                if (isinstance(msg, AIMessage) and 
                    msg.content.strip() and 
                    not (hasattr(msg, 'name') and 
                         msg.name in ['supervisor', 'correction', 'researcher', 'enhancer', 'validator'])):
                    final_response = msg
                    logging.info(f"Final response found in message history: {msg.content[:100]}...")
                    
                    if hasattr(msg, 'additional_kwargs') and 'improvement' in msg.additional_kwargs:
                        improvement_analysis = {"improvement": msg.additional_kwargs['improvement']}
                        logging.info(f"Improvement analysis found in message history: {improvement_analysis}")
                    
                    break

        if final_response is None:
            raise Exception("Agent did not produce a final response.")

        messages_to_store = [
            {
                "role": "human",
                "content": request.content,
                "analysis": None
            },
            {
                "role": "ai",
                "content": final_response.content,
                "analysis": improvement_analysis
            }
        ]
        
        new_conversation = Conversation(
            id=conversation_id,
            user_id=user_id,
            title=title,
            messages=messages_to_store,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(new_conversation)
        db.commit()
        db.refresh(new_conversation)
        
        return models.NewConversationResponse(
            response=final_response.content,
            conversation_id=conversation_id,
            title=title
        )

    except Exception as e:
        db.rollback()
        logging.error(
            f"Error during new conversation creation for user {user_id}: {e}"
        )
        logging.error(traceback.format_exc())
        raise


def add_message_to_conversation(
    db: Session,
    user_id: UUID,
    conversation_id: UUID,
    human_message: str,
    ai_response: str,
    improvement_analysis: dict = None
) -> None:
    """
    Adds new messages to an existing conversation in PostgreSQL.
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
            raise ConversationNotFoundError(conversation_id)
        
        new_messages = [
            {
                "role": "human",
                "content": human_message,
                "analysis": None
            },
            {
                "role": "ai",
                "content": ai_response,
                "analysis": improvement_analysis
            }
        ]
        
        conversation.messages.extend(new_messages)
        conversation.updated_at = datetime.utcnow()
        
        flag_modified(conversation, 'messages')
        
        db.commit()
        logging.info(f"Added messages to conversation {conversation_id} for user {user_id}.")
        
    except ConversationNotFoundError:
        raise
    except Exception as e:
        db.rollback()
        logging.error(f"Error adding message to conversation {conversation_id}: {e}")
        raise

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