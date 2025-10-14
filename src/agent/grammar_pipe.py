from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langchain_groq import ChatGroq

from .language_tool import LanguageToolAPI

class PreprocessingState(TypedDict):
    user_input: str
    syntactic_analysis: str
    semantic_analysis: str

language_tool = LanguageToolAPI()
semantic_llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.1)


def syntactic_check_node(state: PreprocessingState) -> PreprocessingState:
    """Primeiro nó: Roda a análise sintática com LanguageTool."""
    print("[Pipeline LangGraph]: Executando Nó de Análise Sintática...")
    user_input = state['user_input']
    correction_result = language_tool.check_text(user_input)
    
    analysis_str = ""
    if correction_result.errors:
        analysis_str = f"Foram encontrados erros. Texto original: '{correction_result.original_text}'. Correção sugerida: '{correction_result.corrected_text}'. Explicação: {correction_result.explanation}"
    else:
        analysis_str = "Nenhum erro de sintaxe encontrado."
        
    return {"syntactic_analysis": analysis_str}

def semantic_check_node(state: PreprocessingState) -> PreprocessingState:
    """Segundo nó: Roda a análise semântica com um LLM especialista."""
    print("[Pipeline LangGraph]: Executando Nó de Análise Semântica...")
    user_input = state['user_input']
    syntactic_analysis = state['syntactic_analysis']

    prompt = f"""
    You are an expert in English linguistics, focusing on semantics and natural language use for voice conversations.
    Your task is to analyze a sentence from an English learner and find errors that an automatic syntax tool might miss.
    You MUST IGNORE all punctuation errors. The input comes from a voice-to-text system where punctuation is not relevant.

    User's Sentence: "{user_input}"

    Analysis from the Syntactic Tool:
    "{syntactic_analysis}"

    Your Analysis:
    1.  Review the user's sentence.
    2.  Are there any semantic errors, incorrect word choices (e.g., 'their' vs 'there'), or phrases that sound unnatural, even if grammatically correct?
    3.  Provide a clear and concise explanation for each semantic or usage error you find.
    4.  If no additional semantic errors are found, respond ONLY with "No additional semantic errors found.".
    """
    
    response = semantic_llm.invoke(prompt)
    return {"semantic_analysis": response.content}

def create_preprocessing_graph():
    """Cria e compila o grafo LangGraph para o pipeline de pré-processamento."""
    workflow = StateGraph(PreprocessingState)

    workflow.add_node("syntactic_check", syntactic_check_node)
    workflow.add_node("semantic_check", semantic_check_node)

    workflow.add_edge(START, "syntactic_check")
    workflow.add_edge("syntactic_check", "semantic_check")
    workflow.add_edge("semantic_check", END)
    
    return workflow.compile()