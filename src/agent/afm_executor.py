import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_groq import ChatGroq
from langgraph.store.redis import RedisStore
from pydantic import ValidationError

from .afm_prompt_template import MASTER_PROMPT_TEMPLATE
from .tools import execute_tool
from .tool_schemas import SaveGrammarCorrection, UpdateUserProfile, WebSearch

# Modelo principal do AFM
llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.3)

# Modelo para structured outputs
structured_llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.0)

# Bind schemas usando with_structured_output
websearch_extractor = structured_llm.with_structured_output(WebSearch)
profile_extractor = structured_llm.with_structured_output(UpdateUserProfile)
grammar_extractor = structured_llm.with_structured_output(SaveGrammarCorrection)


async def run_afm_cycle(
    user_input: str,
    conversation_history: list,
    user_profile: str,
    syntactic_analysis: str,
    semantic_analysis: str,
    store: RedisStore,
    user_id: str,
    conversation_id: str,
    db_session: Session
) -> str:
    history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history])
    
    prompt = MASTER_PROMPT_TEMPLATE.format(
        syntactic_analysis=syntactic_analysis,
        semantic_analysis=semantic_analysis,
        history=history_str,
        user_profile=user_profile,
        user_input=user_input,
        conversation_id=conversation_id
    )
    
    messages = [SystemMessage(content=prompt)]
    
    max_turns = 5
    for turn in range(max_turns):
        logging.info(f"AFM Turn {turn + 1}/{max_turns}")
        
        response_ai = llm.invoke(messages)
        response_content = response_ai.content
        
        print("\n" + "="*20 + f" SAÍDA DO LLM (Turno {turn + 1}) " + "="*20)
        print(response_content)
        print("="*65 + "\n")
        
        messages.append(AIMessage(content=response_content))

        if "<final_answer>" in response_content:
            final_answer = response_content.split("<final_answer>")[1].split("</final_answer>")[0].strip()
            # Retorna apenas a resposta final, sem as outras tags (plan, reflection).
            return final_answer
        
        if "<tool_call>" in response_content:
            tool_call_content = response_content.split("<tool_call>")[1].split("</tool_call>")[0].strip()
            
            try:
                print(f"[...Processando chamada de ferramenta: '{tool_call_content}']")
                
                extractor = None
                tool_name = None
                
                if "WebSearch" in tool_call_content:
                    extractor = websearch_extractor
                    tool_name = "WebSearch"
                elif "UpdateUserProfile" in tool_call_content:
                    extractor = profile_extractor
                    tool_name = "UpdateUserProfile"
                elif "SaveGrammarCorrection" in tool_call_content:
                    extractor = grammar_extractor
                    tool_name = "SaveGrammarCorrection"
                else:
                    raise ValueError(f"Tool not recognized in: {tool_call_content}") # Traduzido
                
                logging.info(f"AFM Tool Call: {tool_name}")
                print(f"[...Usando structured output para extrair parâmetros de {tool_name}...]")
                
                extraction_prompt = f"""Extract the parameters from this function call and return them in the correct schema format:

{tool_call_content}

Parse the function call and extract all parameters."""
                
                tool_params_obj = extractor.invoke([HumanMessage(content=extraction_prompt)])
                print(f"[...Objeto Pydantic extraído: {tool_params_obj}]")
                
                tool_params = tool_params_obj.model_dump()
                tool_params['user_id'] = user_id
                tool_params['store'] = store
                tool_params['db_session'] = db_session
                tool_params['conversation_id'] = conversation_id
                
                tool_result = await execute_tool(tool_name, tool_params)
                
                observation_message = HumanMessage(content=f"<observation>\n{tool_result}\n</observation>")
                messages.append(observation_message)

            except ValidationError as e:
                logging.error(f"Pydantic validation error: {e}", exc_info=True)
                error_message = HumanMessage(content=f"<observation>\nPydantic validation error: {e}\n</observation>")
                messages.append(error_message)
                
            except Exception as e:
                logging.error(f"Failed to execute tool call: {e}", exc_info=True)
                error_message = HumanMessage(content=f"<observation>\nError executing tool: {e}\n</observation>")
                messages.append(error_message)
        else:
            logging.warning("AFM did not produce a final answer or a tool call. Returning last raw content.")
            return response_content.strip()

    return "I'm sorry, I couldn't process your request after several attempts."