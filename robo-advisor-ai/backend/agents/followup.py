"""
RoboAdvisor AI — Follow-up Agent
Handles post-strategy questions and rebalancing requests.
Has full context: profile, research, strategy, allocations.
"""

import os
import json
import anthropic
from status import emit_status


client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

FOLLOWUP_SYSTEM = """You are a portfolio advisor answering follow-up questions about a portfolio you just built.

You have full context below. Answer questions directly, concisely, and with specific numbers from the data.

INVESTMENT PROFILE:
{profile}

PORTFOLIO ALLOCATION:
{allocations}

PORTFOLIO STATS:
- Expected annual return: {expected_return:.1%}
- Expected volatility: {volatility:.1%}
- Sharpe ratio: {sharpe:.2f}

STRATEGY REASONING:
{reasoning}

RESEARCH DATA:
{research}

RULES:
- Be specific — reference actual numbers, tickers, and weights
- If asked "what if" scenarios, reason through the impact qualitatively
- If asked to explain a concept (Sharpe ratio, Black-Litterman), explain it simply
- If asked why a ticker was chosen or weighted a certain way, reference the research data
- Keep answers concise — 2-4 sentences for simple questions, more for complex ones
- NEVER use LaTeX notation — write math in plain text"""


REBALANCE_DETECT_PROMPT = """You are classifying a user message about their investment portfolio.

Determine if the user wants to MODIFY their portfolio or just ASK A QUESTION about it.

MODIFY means: add a ticker, remove a ticker, change allocation weights, change risk level, change sectors, rebuild the portfolio, or any request that requires re-running the optimizer.

Examples of MODIFY:
- "Add TSLA to the portfolio"
- "Remove INTC"
- "Reduce NVDA to 10%"
- "Make it more conservative"
- "I want more healthcare exposure"
- "Rebuild with less tech"
- "What if we added some bonds?"

Examples of QUESTION (not modify):
- "Why is NVDA weighted so high?"
- "What's the Sharpe ratio mean?"
- "Explain the strategy"
- "What happens if NVDA drops 20%?"
- "How diversified is this?"

Respond with ONLY a JSON object:
{"intent": "modify" or "question", "modifications": "brief description of what to change" or null}"""


def detect_rebalance(user_message: str) -> dict:
    """Use Haiku to detect if the user wants to modify the portfolio."""
    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=150,
            messages=[{"role": "user", "content": user_message}],
            system=REBALANCE_DETECT_PROMPT,
        )
        raw = response.content[0].text.strip()
        # Extract JSON
        if "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()
            if raw.startswith("json"):
                raw = raw[4:].strip()
        match = None
        import re
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            match = json.loads(json_match.group())
        else:
            match = json.loads(raw)
        return match
    except Exception:
        return {"intent": "question", "modifications": None}


def followup_agent(user_message: str, state: dict) -> str:
    """
    Answer a follow-up question using the full portfolio context.
    Returns the response text.
    """
    emit_status("💬 Answering your question...")
    
    profile = state.get("investment_profile", {})
    strategy = state.get("strategy", {})
    research = state.get("research_results", [])
    
    # Build allocations summary
    alloc_lines = []
    for a in strategy.get("allocations", []):
        if a.get("weight", 0) > 0.001:
            alloc_lines.append(
                f"  {a['ticker']}: {a['weight']:.1%} — ${a.get('dollar_amount', 0):,.0f} (~{a.get('shares', 0)} shares)"
            )
    alloc_text = "\n".join(alloc_lines) or "No allocations available"
    
    # Build research summary
    research_lines = []
    for r in research:
        f = r.get("fundamentals", {})
        t = r.get("technicals", {})
        s = r.get("sentiment", {})
        research_lines.append(
            f"  {r['ticker']} ({r.get('company_name', 'N/A')}): "
            f"${r.get('current_price', 0):.2f}, "
            f"P/E {f.get('pe_ratio', 'N/A')}, "
            f"RSI {t.get('rsi_14', 'N/A')}, "
            f"Sentiment {s.get('score', 0):.1f}"
        )
    research_text = "\n".join(research_lines) or "No research data available"
    
    system = FOLLOWUP_SYSTEM.format(
        profile=json.dumps(profile, indent=2, default=str),
        allocations=alloc_text,
        expected_return=strategy.get("expected_annual_return", 0),
        volatility=strategy.get("expected_volatility", 0),
        sharpe=strategy.get("sharpe_ratio", 0),
        reasoning=strategy.get("reasoning", "N/A"),
        research=research_text,
    )
    
    # Build conversation history (last 10 messages — user message already included)
    messages = []
    for msg in state.get("messages", [])[-10:]:
        messages.append({
            "role": msg["role"],
            "content": msg["content"],
        })
    
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=600,
        system=system,
        messages=messages,
    )
    
    return response.content[0].text


def rebalance_agent(user_message: str, modifications: str, state: dict) -> dict:
    """
    Handle a rebalancing request. Updates the profile with new constraints
    and resets the phase so the graph re-runs research + strategy.
    Returns the updated state (not just text).
    """
    emit_status("🔄 Preparing to rebalance your portfolio...")
    
    profile = state.get("investment_profile", {})
    current_tickers = state.get("tickers", [])
    
    # Use Claude to update the profile based on the modification request
    update_prompt = f"""Given the current investment profile and modification request, output an updated profile as JSON.

Current profile:
{json.dumps(profile, indent=2, default=str)}

Current tickers in portfolio: {', '.join(current_tickers)}

Modification requested: {modifications}
User message: {user_message}

Rules:
- Keep all existing fields, only change what the user asked to change
- If adding tickers, add them to sector_preferences or note them in constraints
- If removing tickers, add "exclude: TICKER" to constraints
- If changing risk, update risk_tolerance and risk_category
- Output ONLY the updated JSON, wrapped in ```json tags
- Keep profile_complete: true"""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        messages=[{"role": "user", "content": update_prompt}],
    )
    
    raw = response.content[0].text.strip()
    
    # Parse updated profile
    try:
        if "```json" in raw:
            json_str = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            json_str = raw.split("```")[1].split("```")[0].strip()
        else:
            json_str = raw
        updated_profile = json.loads(json_str)
        updated_profile["profile_complete"] = True
        if "raw_input" not in updated_profile:
            updated_profile["raw_input"] = profile.get("raw_input", "")
    except Exception:
        # If parsing fails, just add the modification as a constraint
        updated_profile = profile.copy()
        constraints = updated_profile.get("constraints", [])
        constraints.append(modifications)
        updated_profile["constraints"] = constraints
    
    # Acknowledge the rebalance
    ack_message = f"Got it — adjusting your portfolio based on: {modifications}. Researching new allocations now..."
    
    # Reset state for re-run
    state["investment_profile"] = updated_profile
    state["profile_complete"] = True
    state["phase"] = "intake"  # Reset so graph re-runs
    state["strategy"] = None
    state["research_results"] = []
    state["tickers"] = []
    state["market_caps"] = {}
    state["covariance_matrix"] = None
    state["messages"] = state.get("messages", []) + [
        {"role": "assistant", "content": ack_message}
    ]
    
    return state