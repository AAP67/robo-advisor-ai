"""
RoboAdvisor AI — Intake Agent
Parses natural language into a structured InvestmentProfile.
Asks follow-up questions if information is missing.
"""

import os
import json
import anthropic
from agents.state import AgentState


client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """You are the Intake Agent of an AI robo-advisor. Your job is to extract a structured investment profile from the user's message.

You need these fields:
- capital: Total investable amount in USD (required)
- risk_tolerance: 1-10 scale, 1=very conservative, 10=very aggressive (required)
- horizon_years: Investment time horizon in years (required)
- sector_preferences: List of preferred sectors/themes (optional, default [])
- constraints: Exclusions like "no tobacco", "no weapons" (optional, default [])
- existing_holdings: Current positions as {ticker: dollar_value} (optional, default {})

RULES:
1. If ALL three required fields (capital, risk_tolerance, horizon_years) can be inferred from the conversation, respond with ONLY a JSON block wrapped in ```json tags.
2. If ANY required field is missing or ambiguous, ask a friendly follow-up question. Be conversational, not robotic. Ask about only the missing fields.
3. For risk_tolerance, you can infer from words like "conservative" (2-3), "moderate" (4-6), "aggressive" (7-8), "very aggressive" (9-10).
4. For horizon_years, infer from phrases like "retirement in 20 years" (20), "short term" (1-2), "long term" (10+).

When outputting the profile JSON, use this exact format:
```json
{
    "capital": 50000,
    "risk_tolerance": 5,
    "risk_category": "moderate",
    "horizon_years": 3,
    "sector_preferences": ["technology", "AI"],
    "constraints": [],
    "existing_holdings": {},
    "profile_complete": true
}
```

risk_category must be one of: "conservative" (1-3), "moderate" (4-6), "aggressive" (7-9), "very_aggressive" (10)."""


def intake_agent(state: AgentState) -> dict:
    """
    Parse user input into an investment profile.
    Returns updated state fields.
    """
    # Build conversation for Claude
    messages = []
    for msg in state["messages"]:
        messages.append({
            "role": msg["role"],
            "content": msg["content"],
        })
    
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=messages,
    )
    
    reply = response.content[0].text
    
    # Try to extract JSON profile from the response
    profile = _extract_profile(reply)
    
    if profile and profile.get("profile_complete"):
        # Get the raw user input (first user message)
        raw_input = ""
        for msg in state["messages"]:
            if msg["role"] == "user":
                raw_input = msg["content"]
                break
        
        profile["raw_input"] = raw_input
        
        # Clean reply for the user — just confirm, don't show JSON
        clean_reply = _make_confirmation(profile)
        
        return {
            "messages": [{"role": "assistant", "content": clean_reply}],
            "investment_profile": profile,
            "profile_complete": True,
            "current_agent": "research",
        }
    else:
        # Claude is asking a follow-up question
        return {
            "messages": [{"role": "assistant", "content": reply}],
            "profile_complete": False,
            "current_agent": "intake",
        }


def _extract_profile(text: str) -> dict | None:
    """Try to extract JSON profile from Claude's response."""
    try:
        # Look for ```json block
        if "```json" in text:
            json_str = text.split("```json")[1].split("```")[0].strip()
            return json.loads(json_str)
        elif "```" in text:
            json_str = text.split("```")[1].split("```")[0].strip()
            return json.loads(json_str)
        # Try parsing the whole thing as JSON
        return json.loads(text.strip())
    except (json.JSONDecodeError, IndexError):
        return None


def _make_confirmation(profile: dict) -> str:
    """Generate a friendly confirmation message."""
    risk_labels = {
        "conservative": "conservative",
        "moderate": "moderate",
        "aggressive": "aggressive",
        "very_aggressive": "very aggressive",
    }
    risk_label = risk_labels.get(profile.get("risk_category", ""), "moderate")
    
    sectors = profile.get("sector_preferences", [])
    sector_text = f", focusing on {', '.join(sectors)}" if sectors else ""
    
    constraints = profile.get("constraints", [])
    constraint_text = f" Exclusions: {', '.join(constraints)}." if constraints else ""
    
    return (
        f"Got it! Here's what I'm working with:\n\n"
        f"• **Capital**: ${profile['capital']:,.0f}\n"
        f"• **Risk tolerance**: {risk_label} ({profile['risk_tolerance']}/10)\n"
        f"• **Time horizon**: {profile['horizon_years']} years{sector_text}\n"
        f"{constraint_text}\n\n"
        f"Now let me research the best assets for your portfolio. This will take a moment..."
    )
