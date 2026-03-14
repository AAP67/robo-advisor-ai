"""
Test the full LangGraph agent pipeline end-to-end.
Run: cd backend && python -m tests.test_graph

This runs the full pipeline: Intake → Research → Strategy
Uses real API calls (Claude, yfinance, NewsAPI).
Takes ~30-60 seconds.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from graph import run_advisor, get_last_response


def test_complete_input():
    """Test with a complete investment paragraph — should go through all 3 agents."""
    
    print("=" * 60)
    print("TEST: Complete input (Intake → Research → Strategy)")
    print("=" * 60)
    
    user_input = (
        "I have $100,000 to invest. I'm moderately aggressive with risk, "
        "maybe a 7 out of 10. I'm interested in AI and technology companies. "
        "I have a 5-year horizon. No tobacco or weapons companies please."
    )
    
    print(f"\n👤 User: {user_input}\n")
    print("─" * 60)
    
    state = run_advisor(user_input)
    
    # Print all assistant messages
    for msg in state["messages"]:
        if msg["role"] == "assistant":
            print(f"\n🤖 Assistant:\n{msg['content']}")
            print("─" * 60)
    
    # Verify results
    assert state.get("profile_complete"), "Profile should be complete"
    assert state.get("investment_profile"), "Should have investment profile"
    assert len(state.get("research_results", [])) > 0, "Should have research results"
    assert state.get("strategy"), "Should have strategy"
    
    profile = state["investment_profile"]
    strategy = state["strategy"]
    
    print(f"\n✅ Profile: ${profile['capital']:,.0f}, risk {profile['risk_tolerance']}/10, {profile['horizon_years']}yr")
    print(f"✅ Researched {len(state['research_results'])} tickers")
    print(f"✅ Strategy: {strategy['expected_annual_return']:.1%} return, {strategy['sharpe_ratio']:.2f} Sharpe")
    print(f"✅ Allocations: {len(strategy['allocations'])} positions")
    
    return state


def test_incomplete_input():
    """Test with incomplete input — Intake should ask follow-up questions."""
    
    print("\n" + "=" * 60)
    print("TEST: Incomplete input (Intake should ask follow-ups)")
    print("=" * 60)
    
    user_input = "I want to invest in tech stocks"
    
    print(f"\n👤 User: {user_input}\n")
    
    state = run_advisor(user_input)
    response = get_last_response(state)
    
    print(f"🤖 Assistant: {response}\n")
    
    # Should NOT be complete — missing capital, risk, horizon
    assert not state.get("profile_complete"), "Profile should be incomplete"
    assert not state.get("strategy"), "Should not have strategy yet"
    
    print("✅ Correctly asked for more information")
    
    # Now provide the missing info
    print("\n👤 User: I have $50K, moderate risk, 3 year horizon\n")
    
    state = run_advisor("I have $50K, moderate risk, 3 year horizon", state)
    
    for msg in state["messages"]:
        if msg["role"] == "assistant":
            print(f"🤖 Assistant:\n{msg['content']}")
            print("─" * 60)
    
    if state.get("strategy"):
        print(f"\n✅ Multi-turn conversation worked!")
        print(f"✅ Strategy generated after follow-up")
    
    return state


if __name__ == "__main__":
    print("\n🚀 Running full pipeline test...\n")
    
    # Test 1: Complete input (full pipeline)
    state1 = test_complete_input()
    
    # Test 2: Incomplete input (multi-turn)
    # Uncomment to test — this makes extra API calls
    # state2 = test_incomplete_input()
    
    print("\n🎉 Step 4 complete! Agent graph is working.")
