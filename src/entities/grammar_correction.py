from sqlalchemy import Column, String, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from ..database.core import Base
from sqlalchemy.orm import relationship

import uuid
from .message import Message

class GrammarCorrection(Base):
    __tablename__ = 'grammar_corrections'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Correção agora pertence a uma mensagem específica.
    message_id = Column(UUID(as_uuid=True), ForeignKey('messages.id'), nullable=False, unique=True)
    # -----------------------------------------
    
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    
    original_text = Column(Text, nullable=False)
    corrected_text = Column(Text, nullable=False)
    explanation = Column(Text, nullable=False)
    improvement = Column(Text, nullable=False)

    message = relationship("Message", back_populates="correction")
    # ---------------------------------

    def __repr__(self):
        return f"<GrammarCorrection(id='{self.id}', message_id='{self.message_id}')>"