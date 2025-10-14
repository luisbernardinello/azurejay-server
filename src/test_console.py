import asyncio
import logging
import os
import uuid
from dotenv import load_dotenv
from unittest.mock import MagicMock
from sqlalchemy.orm import Session

load_dotenv()
os.environ["REDIS_URL"] = os.getenv("REDIS_URL_LOCAL", "redis://localhost:6379/0")

from .agent.afm_executor import run_afm_cycle
from .agent.grammar_pipe import create_preprocessing_graph
from .database.core import store_instance as store
from .entities.user import User
from .entities.conversation import Conversation

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

preprocessing_graph = create_preprocessing_graph()

async def chat_session():
    if store is None:
        logging.error("A conexão com o Redis pelo LangGraph Store falhou.")
        return

    print("_____Teste de Console do Chatbot com AFM_____")
    user_id = "a1b2c3d4-e5f6-7890-1234-56789abcdef0"
    conversation_id = str(uuid.uuid4())
    print(f"ID de Usuário da Sessão: {user_id}")
    print(f"ID da Conversa da Sessão: {conversation_id}")
    print("Digite 'sair' a qualquer momento para terminar a sessão.")
    print("-" * 60)

    conversation_history = []

    while True:
        try:
            profile_namespace = ("profile", user_id)
            existing_profile_items = store.search(profile_namespace)
            
            user_profile_str = "Nenhum perfil salvo ainda."
            if existing_profile_items:
                user_profile_str = str(existing_profile_items[0].value)
            print(f"\n[Memória de Perfil Carregada]: {user_profile_str}")
            
            # Leitura da Memória de Correções
            corrections_namespace = ("corrections", user_id, conversation_id)
            existing_corrections = store.search(corrections_namespace)
            print(f"[Memória de Correções (Sessão Atual)]: {len(existing_corrections)} correções salvas.")
            if existing_corrections:
                for i, item in enumerate(existing_corrections):
                    print(f"  - Correção {i+1}: {item.value}")
            
            user_input = input("\nVocê: ")
            if user_input.lower().strip() in ["sair", "exit", "quit"]:
                break

            print("\n[...Iniciando Pipeline de Pré-Processamento LangGraph...]")
            initial_state = {"user_input": user_input}
            final_state = preprocessing_graph.invoke(initial_state)
            
            syntactic_analysis = final_state.get("syntactic_analysis", "Erro na análise sintática.")
            semantic_analysis = final_state.get("semantic_analysis", "Erro na análise semântica.")
            
            print(f"[Análise Sintática (Nó 1 - LanguageTool)]: {syntactic_analysis}")
            print(f"[Análise Semântica (Nó 2 - LLM Especialista)]: {semantic_analysis}")
            
            conversation_history.append({"role": "user", "content": user_input})
            print("\n[...Delegando ao Agente AFM para Raciocínio e Resposta...]")
            
            mock_db_session = MagicMock(spec=Session)
            mock_user = User(id=user_id, first_name="Alex", user_interests=[], location=None)
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            final_answer = await run_afm_cycle(
                user_input=user_input,
                conversation_history=conversation_history,
                user_profile=user_profile_str,
                syntactic_analysis=syntactic_analysis,
                semantic_analysis=semantic_analysis,
                store=store, 
                user_id=user_id,
                db_session=mock_db_session,
                conversation_id=conversation_id
            )
            
            print(f"\nRachel (AFM): {final_answer}")
            conversation_history.append({"role": "ai", "content": final_answer})

        except KeyboardInterrupt:
            print("\n\nEncerrando o chat.")
            break
        except Exception as e:
            logging.error(f"Ocorreu um erro: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(chat_session())