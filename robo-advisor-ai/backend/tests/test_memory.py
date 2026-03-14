"""
Test the Supabase memory layer end-to-end.
Run: cd backend && python -m tests.test_memory

Requires SUPABASE_URL and SUPABASE_ANON_KEY in .env
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from db.memory import Memory


def test_full_flow():
    mem = Memory()
    
    # 1. Create session
    session_id = mem.create_session()
    print(f"✅ Created session: {session_id}")
    
    # 2. Save messages
    mem.save_message(session_id, "user", "I have $50K to invest, moderate risk, bullish on AI")
    mem.save_message(
        session_id,
        "assistant",
        "Got it! Let me parse your investment profile.",
        metadata={"agent": "intake"}
    )
    messages = mem.get_messages(session_id)
    assert len(messages) == 2
    print(f"✅ Saved & retrieved {len(messages)} messages")
    
    # 3. Save profile
    profile = {
        "capital": 50000,
        "risk_tolerance": 5,
        "risk_category": "moderate",
        "horizon_years": 3,
        "sector_preferences": ["technology", "AI"],
        "constraints": [],
        "existing_holdings": {},
        "raw_input": "I have $50K to invest, moderate risk, bullish on AI",
    }
    mem.save_profile(session_id, profile)
    loaded_profile = mem.get_profile(session_id)
    assert loaded_profile["capital"] == 50000
    print(f"✅ Saved & retrieved profile (capital: ${loaded_profile['capital']:,.0f})")
    
    # 4. Save research cache
    research = {
        "current_price": 195.50,
        "fundamentals": {"pe_ratio": 28.5, "revenue_growth_yoy": 0.12},
        "technicals": {"rsi_14": 62.3, "macd": 1.5},
        "sentiment": {"score": 0.7, "summary": "Positive AI momentum"},
    }
    mem.save_research("AAPL", research)
    cached = mem.get_cached_research("AAPL", max_age_hours=1)
    assert cached is not None
    print(f"✅ Saved & retrieved AAPL research (price: ${cached['current_price']})")
    
    # 5. Save strategy
    strategy = {
        "allocations": [
            {"ticker": "AAPL", "weight": 0.35, "rationale": "Strong AI play"},
            {"ticker": "MSFT", "weight": 0.35, "rationale": "Cloud + AI leader"},
            {"ticker": "GOOGL", "weight": 0.30, "rationale": "Undervalued AI assets"},
        ],
        "expected_annual_return": 0.12,
        "expected_volatility": 0.18,
        "sharpe_ratio": 0.42,
        "bl_params": {"tau": 0.05, "risk_aversion": 2.5},
        "reasoning": "Concentrated AI portfolio with moderate risk",
        "tickers_researched": ["AAPL", "MSFT", "GOOGL"],
    }
    mem.save_strategy(session_id, strategy)
    latest = mem.get_latest_strategy(session_id)
    assert latest["sharpe_ratio"] == 0.42
    print(f"✅ Saved & retrieved strategy (Sharpe: {latest['sharpe_ratio']})")
    
    # 6. Load full session
    full = mem.load_full_session(session_id)
    assert full["session"] is not None
    assert len(full["messages"]) == 2
    assert full["profile"] is not None
    assert len(full["strategies"]) == 1
    print(f"✅ Full session load works")
    
    # 7. List sessions
    sessions = mem.list_sessions(limit=5)
    assert len(sessions) >= 1
    print(f"✅ Listed {len(sessions)} recent session(s)")
    
    print(f"\n🎉 All memory tests passed! Session ID: {session_id}")


if __name__ == "__main__":
    test_full_flow()
