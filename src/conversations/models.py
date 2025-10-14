from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import List, Literal, Optional

from src.entities.message import MessageRole

class ConversationListItem(BaseModel):
    """Representa um item na lista de conversas do usuário."""
    id: UUID
    title: str
    updated_at: datetime

class GrammarCorrectionDetail(BaseModel):
    """Representa os detalhes de uma correção gramatical vinculada a uma mensagem."""
    original_text: str
    corrected_text: str
    explanation: str
    improvement: str

class MessageDetail(BaseModel):
    """Representa uma única mensagem detalhada no histórico de uma conversa."""
    id: UUID
    role: MessageRole
    content: str
    correction: Optional[GrammarCorrectionDetail] = None

class ConversationHistoryResponse(BaseModel):
    """Representa o histórico completo de uma conversa específica."""
    id: UUID
    title: str
    messages: List[MessageDetail]

class NewConversationRequest(BaseModel):
    """Define a estrutura para criar uma nova conversa com a primeira mensagem."""
    content: str = Field(..., description="O conteúdo da primeira mensagem do usuário.")

class NewConversationResponse(BaseModel):
    """Define a resposta ao criar uma nova conversa."""
    response: str
    conversation_id: UUID
    title: str

class ChatRequest(BaseModel):
    """Define a estrutura para enviar uma nova mensagem para uma conversa existente."""
    content: str = Field(..., description="O conteúdo da nova mensagem do usuário.")

class ChatResponse(BaseModel):
    """Define a resposta para uma nova mensagem em uma conversa existente."""
    response: str