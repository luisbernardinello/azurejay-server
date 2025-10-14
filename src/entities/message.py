from enum import Enum
import enum
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum as SQLAlchemyEnum 
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from ..database.core import Base

class MessageRole(str, enum.Enum):
    HUMAN = "human"
    AI = "ai"

class Message(Base):
    __tablename__ = 'messages'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey('conversations.id'), nullable=False)
    
    # 'human' para o usuário, 'ai' para o agente
    role = Column(SQLAlchemyEnum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relacionamento de volta para a conversa
    conversation = relationship("Conversation", back_populates="messages")
    
    # Relacionamento para a correção gramatical (uma mensagem pode ter uma correção)
    correction = relationship("GrammarCorrection", back_populates="message", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Message(id='{self.id}', role='{self.role}')>"