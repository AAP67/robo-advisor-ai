"""
Test the FastAPI backend.
Run: 
  1. Start server: cd backend && uvicorn main:app --reload
  2. In another terminal: cd backend && python -m tests.test_api
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import json

BASE = "http://localhost:8000"


def test_health():
    """Test health endpoint."""
    resp = requests.get(f"{BASE}/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    print(f"✅ Health check: {data}")


def test_chat_incomplete():
    """Test chat with incomplete input — should ask follow-ups."""
    resp = requests.post(f"{BASE}/chat", json={
        "message": "I want to invest in tech stocks"
    })
    assert resp.status_code == 200
    data = resp.json()
    
    assert data["session_id"], "Should have session ID"
    assert not data["profile_complete"], "Profile should be incomplete"
    assert data["response"], "Should have a response"
    
    print(f"✅ Incomplete input test")
    print(f"   Session: {data['session_id']}")
    print(f"   Response: {data['response'][:100]}...")
    
    return data["session_id"]


def test_chat_complete():
    """Test chat with complete input — should run full pipeline."""
    print("\n⏳ Running full pipeline (30-60 seconds)...")
    
    resp = requests.post(f"{BASE}/chat", json={
        "message": (
            "I have $75,000 to invest with moderate risk tolerance, "
            "about 5 out of 10. Interested in AI and clean energy. "
            "3 year time horizon."
        )
    }, timeout=120)
    
    assert resp.status_code == 200
    data = resp.json()
    
    assert data["profile_complete"], "Profile should be complete"
    assert data["strategy"], "Should have strategy"
    assert len(data["strategy"]["allocations"]) > 0, "Should have allocations"
    
    print(f"✅ Complete input test")
    print(f"   Session: {data['session_id']}")
    print(f"   Allocations: {len(data['strategy']['allocations'])} positions")
    print(f"   Return: {data['strategy']['expected_annual_return']:.1%}")
    print(f"   Sharpe: {data['strategy']['sharpe_ratio']:.2f}")
    
    return data


def test_sessions():
    """Test session listing."""
    resp = requests.get(f"{BASE}/sessions")
    assert resp.status_code == 200
    data = resp.json()
    print(f"✅ Sessions: {len(data['sessions'])} found")


if __name__ == "__main__":
    print("🧪 Testing FastAPI backend...\n")
    
    test_health()
    session_id = test_chat_incomplete()
    test_sessions()
    
    # Uncomment for full pipeline test (takes 30-60 seconds):
    # test_chat_complete()
    
    print("\n🎉 API tests passed!")
