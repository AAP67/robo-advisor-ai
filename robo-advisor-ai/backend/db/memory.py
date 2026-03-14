"""
RoboAdvisor AI — Memory Layer
Save/load conversations, profiles, research, and strategies to Supabase.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from db.supabase_client import get_supabase_client


class Memory:
    """Persistent memory backed by Supabase."""
    
    def __init__(self):
        self.db = get_supabase_client()
    
    # ── Sessions ──
    
    def create_session(self) -> str:
        """Create a new session, return session_id."""
        result = self.db.table("sessions").insert({}).execute()
        return result.data[0]["id"]
    
    def get_session(self, session_id: str) -> Optional[dict]:
        """Get session by ID."""
        result = (
            self.db.table("sessions")
            .select("*")
            .eq("id", session_id)
            .execute()
        )
        return result.data[0] if result.data else None
    
    def list_sessions(self, limit: int = 10) -> list[dict]:
        """List recent sessions."""
        result = (
            self.db.table("sessions")
            .select("*")
            .order("updated_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data
    
    # ── Messages ──
    
    def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Save a message to the conversation history."""
        row = {
            "session_id": session_id,
            "role": role,
            "content": content,
            "metadata": metadata or {},
        }
        result = self.db.table("messages").insert(row).execute()
        return result.data[0]
    
    def get_messages(self, session_id: str) -> list[dict]:
        """Get full conversation history for a session, chronological."""
        result = (
            self.db.table("messages")
            .select("*")
            .eq("session_id", session_id)
            .order("created_at", desc=False)
            .execute()
        )
        return result.data
    
    # ── Investment Profiles ──
    
    def save_profile(self, session_id: str, profile: dict) -> dict:
        """Save parsed investment profile."""
        row = {
            "session_id": session_id,
            "capital": profile["capital"],
            "risk_tolerance": profile["risk_tolerance"],
            "risk_category": profile["risk_category"],
            "horizon_years": profile["horizon_years"],
            "sector_preferences": profile.get("sector_preferences", []),
            "constraints": profile.get("constraints", []),
            "existing_holdings": profile.get("existing_holdings", {}),
            "raw_input": profile["raw_input"],
        }
        result = self.db.table("investment_profiles").insert(row).execute()
        return result.data[0]
    
    def get_profile(self, session_id: str) -> Optional[dict]:
        """Get the latest profile for a session."""
        result = (
            self.db.table("investment_profiles")
            .select("*")
            .eq("session_id", session_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
    
    # ── Research Cache ──
    
    def save_research(self, ticker: str, research_data: dict) -> dict:
        """Cache research for a ticker."""
        row = {
            "ticker": ticker.upper(),
            "current_price": research_data.get("current_price"),
            "fundamentals": research_data.get("fundamentals", {}),
            "technicals": research_data.get("technicals", {}),
            "sentiment": research_data.get("sentiment", {}),
        }
        result = self.db.table("research_cache").insert(row).execute()
        return result.data[0]
    
    def get_cached_research(
        self, ticker: str, max_age_hours: int = 1
    ) -> Optional[dict]:
        """Get cached research if it's fresh enough."""
        cutoff = (
            datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        ).isoformat()
        
        result = (
            self.db.table("research_cache")
            .select("*")
            .eq("ticker", ticker.upper())
            .gte("fetched_at", cutoff)
            .order("fetched_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
    
    # ── Strategies ──
    
    def save_strategy(self, session_id: str, strategy: dict) -> dict:
        """Save a portfolio strategy."""
        row = {
            "session_id": session_id,
            "allocations": strategy["allocations"],
            "expected_annual_return": strategy.get("expected_annual_return"),
            "expected_volatility": strategy.get("expected_volatility"),
            "sharpe_ratio": strategy.get("sharpe_ratio"),
            "bl_params": strategy.get("bl_params", {}),
            "reasoning": strategy.get("reasoning"),
            "tickers_researched": strategy.get("tickers_researched", []),
        }
        result = self.db.table("strategies").insert(row).execute()
        return result.data[0]
    
    def get_strategies(self, session_id: str) -> list[dict]:
        """Get all strategies for a session, newest first."""
        result = (
            self.db.table("strategies")
            .select("*")
            .eq("session_id", session_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data
    
    def get_latest_strategy(self, session_id: str) -> Optional[dict]:
        """Get the most recent strategy for a session."""
        strategies = self.get_strategies(session_id)
        return strategies[0] if strategies else None
    
    # ── Full Session Load (for conversation continuity) ──
    
    def load_full_session(self, session_id: str) -> Optional[dict]:
        """Load everything for a session — messages, profile, strategies."""
        session = self.get_session(session_id)
        if not session:
            return None
        
        return {
            "session": session,
            "messages": self.get_messages(session_id),
            "profile": self.get_profile(session_id),
            "strategies": self.get_strategies(session_id),
        }
