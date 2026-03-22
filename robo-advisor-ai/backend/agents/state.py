"""
RoboAdvisor AI — Agent Graph State
The shared clipboard that all agents read from and write to.
"""

from typing import Optional, Annotated
from typing_extensions import TypedDict
import operator


class AgentState(TypedDict):
    """
    Shared state passed through the LangGraph agent pipeline.
    
    Each agent reads what it needs and writes its output.
    The 'messages' field accumulates — every agent appends, nothing gets overwritten.
    """
    
    # Conversation history (accumulates via operator.add)
    messages: Annotated[list[dict], operator.add]
    
    # Session tracking
    session_id: Optional[str]
    
    # Intake Agent output
    investment_profile: Optional[dict]   # Parsed InvestmentProfile
    profile_complete: bool               # Is the profile ready for research?
    
    # Research Agent output
    tickers: list[str]                   # Tickers selected for research
    research_results: list[dict]         # List of AssetResearch dicts
    market_caps: dict                    # {ticker: market_cap}
    covariance_matrix: Optional[dict]    # {matrix: [...], tickers: [...]}
    
    # Strategy Agent output
    strategy: Optional[dict]             # PortfolioStrategy dict
    
    # Control flow
    current_agent: str                   # Which agent is active
    error: Optional[str]                 # Error message if something fails
    phase: str                           # "intake", "researching", "complete" — controls post-strategy routing