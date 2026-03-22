"""
RoboAdvisor AI — LangGraph Orchestration
Connects Intake → Research → Strategy with conditional routing.

Flow:
  START → Intake → (profile complete?) 
    → No  → wait for user input → Intake again
    → Yes → Research → Strategy → END
"""

from typing import Callable, Optional
from langgraph.graph import StateGraph, END
from agents.state import AgentState
from agents.intake import intake_agent
from agents.research import research_agent
from agents.strategy import strategy_agent
from status import set_status_callback


def should_continue_intake(state: AgentState) -> str:
    """Route after Intake: continue to Research if profile is complete, else stop for user input."""
    if state.get("profile_complete"):
        return "research"
    return "wait_for_input"


def build_graph() -> StateGraph:
    """Build and compile the agent graph."""
    
    graph = StateGraph(AgentState)
    
    # Add nodes (each agent is a node)
    graph.add_node("intake", intake_agent)
    graph.add_node("research", research_agent)
    graph.add_node("strategy", strategy_agent)
    
    # Set entry point
    graph.set_entry_point("intake")
    
    # Conditional edge after intake
    graph.add_conditional_edges(
        "intake",
        should_continue_intake,
        {
            "research": "research",
            "wait_for_input": END,  # Pause — return to user for more info
        },
    )
    
    # Linear edges for the rest
    graph.add_edge("research", "strategy")
    graph.add_edge("strategy", END)
    
    return graph.compile()


# Singleton compiled graph
advisor_graph = build_graph()


def run_advisor(
    user_message: str,
    state: dict | None = None,
    status_callback: Optional[Callable[[str], None]] = None,
) -> dict:
    """
    Run the advisor graph with a user message.
    
    Args:
        user_message: The user's input
        state: Previous state (for multi-turn conversations). None for first message.
        status_callback: Optional function called with status strings during execution.
    
    Returns:
        Updated state dict with all agent outputs and messages.
    """
    # Set the callback for this thread
    set_status_callback(status_callback)
    
    if state is None:
        # Fresh conversation
        state = {
            "messages": [],
            "session_id": None,
            "investment_profile": None,
            "profile_complete": False,
            "tickers": [],
            "research_results": [],
            "market_caps": {},
            "covariance_matrix": None,
            "strategy": None,
            "current_agent": "intake",
            "error": None,
            "phase": "intake",
        }
    
    # Add user message
    state["messages"] = state.get("messages", []) + [
        {"role": "user", "content": user_message}
    ]
    
    # If portfolio is already complete, classify: question or rebalance?
    if state.get("phase") == "complete" and state.get("strategy"):
        from agents.followup import detect_rebalance, followup_agent, rebalance_agent
        
        intent = detect_rebalance(user_message)
        
        if intent.get("intent") == "modify":
            # Rebalance: update profile, reset state, re-run graph
            modifications = intent.get("modifications", user_message)
            state = rebalance_agent(user_message, modifications, state)
            
            # Now re-run the graph from research → strategy
            result = advisor_graph.invoke(state)
            
            if result.get("strategy"):
                result["phase"] = "complete"
            
            set_status_callback(None)
            return result
        else:
            # Just a question — answer it
            response = followup_agent(user_message, state)
            state["messages"] = state.get("messages", []) + [
                {"role": "assistant", "content": response}
            ]
            set_status_callback(None)
            return state
    
    # Run the graph
    result = advisor_graph.invoke(state)
    
    # Mark phase as complete if strategy was generated
    if result.get("strategy"):
        result["phase"] = "complete"
    
    # Clear callback
    set_status_callback(None)
    
    return result


def get_last_response(state: dict) -> str:
    """Extract the last assistant message from the state."""
    for msg in reversed(state.get("messages", [])):
        if msg["role"] == "assistant":
            return msg["content"]
    return ""