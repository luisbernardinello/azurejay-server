import logging
import uuid
from typing import List, Literal, Optional
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_groq import ChatGroq
from trustcall import create_extractor
from langgraph.store.redis import RedisStore
from sqlalchemy.orm import Session
from .language_tool import LanguageToolAPI
from ..entities.user import User
from ..entities.message import Message, MessageRole
from ..entities.grammar_correction import GrammarCorrection
from langchain_tavily import TavilySearch

language_tool_instance = LanguageToolAPI()

web_search_instance = TavilySearch(
    max_results=2,
    include_answer=False,
    include_raw_content=False
)

# Write-Through Cache Functions (data is simultaneously updated to cache and memory)
async def update_user_profile(
    user_id: str,
    db_session: Session,
    store: RedisStore,
    name: Optional[str] = None,
    location: Optional[str] = None,
    interests_to_add: Optional[List[str]] = None,
    **kwargs
) -> str:
    """Receives already extracted profile data and saves it to the DB and Redis."""
    print("\n[...Ferramenta 'update_user_profile' chamada com dados diretos...]")
    try:
        user_in_db = db_session.query(User).filter(User.id == user_id).first()
        if not user_in_db:
            return f"Error: User with ID {user_id} not found."

        if name: user_in_db.first_name = name
        if location: user_in_db.location = location
        if interests_to_add:
            current_interests = user_in_db.user_interests or []
            user_in_db.user_interests = list(set(current_interests) | set(interests_to_add))
        
        db_session.commit()
        db_session.refresh(user_in_db)

        profile_to_cache = {
            "name": user_in_db.first_name,
            "location": user_in_db.location,
            "interests": user_in_db.user_interests
        }
        store.put(("profile", user_id), "latest", profile_to_cache)
        print(f"[...Cache do Redis atualizado: {profile_to_cache}...]")
        
        return "User profile updated successfully."
    except Exception as e:
        if db_session: db_session.rollback()
        logging.error(f"Error in update_user_profile: {e}", exc_info=True)
        return f"Failed to update profile: {e}"

async def save_grammar_correction(
    user_id: str,
    conversation_id: str,
    db_session: Session,
    store: RedisStore,
    original_text: str,
    corrected_text: str,
    explanation: str,
    improvement: str,
    **kwargs
) -> str:
    """Receives already structured correction data and saves it to the DB and Redis."""
    print("\n[...Ferramenta 'save_grammar_correction' chamada com dados diretos...]")
    try:
        last_human_message = db_session.query(Message).filter(Message.conversation_id == conversation_id, Message.role == MessageRole.HUMAN).order_by(Message.created_at.desc()).first()
        if not last_human_message:
            return "Error: User message not found to link the correction."

        correction_data = {
            "original_text": original_text, "corrected_text": corrected_text,
            "explanation": explanation, "improvement": improvement
        }
        
        new_correction = GrammarCorrection(message_id=last_human_message.id, user_id=user_id, **correction_data)
        db_session.add(new_correction)
        db_session.commit()
        
        store.put(("corrections", user_id, conversation_id), str(uuid.uuid4()), correction_data)
        
        return "Grammar correction saved successfully."
    except Exception as e:
        if db_session: db_session.rollback()
        logging.error(f"Error in save_grammar_correction: {e}", exc_info=True)
        return f"Failed to save correction: {e}"


async def execute_web_search(query: str, **kwargs) -> str:
    """
    Executa busca web usando TavilySearch.
    
    A nova TavilySearch espera um dict: {"query": "..."}
    e retorna um dict com estrutura:
    {
        'query': str,
        'results': [{'title': str, 'url': str, 'content': str, 'score': float}, ...],
        'response_time': float
    }
    """
    try:
        result = web_search_instance.invoke({"query": query})
        
        # Formata a resposta para o AFM
        if isinstance(result, dict) and 'results' in result:
            formatted_results = []
            for item in result['results']:
                formatted_results.append(
                    f"[{item.get('title', 'No title')}]({item.get('url', '')})\n"
                    f"{item.get('content', 'No content')}\n"
                )
            return "\n".join(formatted_results)
        
        # Fallback: retorna como string se o formato for diferente
        return str(result)
        
    except Exception as e:
        logging.error(f"Web search error: {e}", exc_info=True)
        return f"Error performing search: {e}"


TOOL_MAP = {
    "WebSearch": execute_web_search,
    "UpdateUserProfile": update_user_profile,
    "SaveGrammarCorrection": save_grammar_correction,
}


async def execute_tool(tool_name: str, tool_params: dict) -> str:
    """Entry point for executing any tool."""
    if tool_name in TOOL_MAP:
        return await TOOL_MAP[tool_name](**tool_params)
    return f"Error: Tool '{tool_name}' is not recognized."