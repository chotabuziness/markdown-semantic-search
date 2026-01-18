import os
from typing import TypedDict, List, Dict, Any
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .search import SearchService

# Load environment variables (for OPENROUTER_API_KEY)
load_dotenv()

class AgentState(TypedDict):
    query: str
    context: str
    response: str
    db_path: str
    top_k: int

def retrieve_node(state: AgentState) -> Dict[str, Any]:
    """Retrieve relevant context from the database."""
    search_service = SearchService(state['db_path'])
    try:
        context = search_service.get_top_context(state['query'], top_k=state.get('top_k', 5))
        return {"context": context}
    finally:
        search_service.close()

def generate_node(state: AgentState) -> Dict[str, Any]:
    """Generate a natural language response based on the context."""
    # Configure for OpenRouter
    llm = ChatOpenAI(
        model=os.getenv("OPENROUTER_MODEL", "openai/gpt-5-nano"),
        openai_api_key=os.getenv("OPENROUTER_API_KEY"),
        openai_api_base=os.getenv("OPENROUTER_API_BASE"),
        default_headers={
            "HTTP-Referer": "https://github.com/chotabuziness/markdown-semantic-search",
            "X-Title": "Markdown Semantic Search"
        },
        temperature=0.2
    )
    
    system_prompt = (
        "You are a helpful and polite virtual assistant. Your goal is to provide clear, "
        "accurate answers STRICTLY based on the knowledge provided to you. "
        "Structure your answers in a natural, conversational manner. "
        "Do not explicitly mention phrases like 'based on the provided context' or 'the excerpts show'. "
        "CRITICAL: If the answer is not contained within the provided knowledge, or if you are unsure, "
        "you MUST politely apologize and state that you do not have that specific information yet. "
        "NEVER use your own outside knowledge or make assumptions. Do not provide information that isn't "
        "explicitly stated in the provided text."
    )
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Context:\n{state['context']}\n\nQuestion: {state['query']}")
    ]
    
    response = llm.invoke(messages)
    return {"response": response.content}

def create_agent():
    """Create and compile the LangGraph agent."""
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("generate", generate_node)
    
    # Define edges
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", END)
    
    return workflow.compile(checkpointer=MemorySaver())

# Global agent instance
rag_agent = create_agent()
