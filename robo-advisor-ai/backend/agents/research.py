"""
RoboAdvisor AI — Research Agent
Selects relevant tickers based on the investment profile,
then runs the full research pipeline on each.
"""

import os
import json
import anthropic
from agents.state import AgentState
from tools.research_pipeline import ResearchPipeline


client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

TICKER_SELECTION_PROMPT = """You are a portfolio research analyst. Given the following investment profile, select 5-8 stock tickers that best match the investor's goals.

Investment Profile:
- Capital: ${capital:,.0f}
- Risk tolerance: {risk_category} ({risk_tolerance}/10)
- Time horizon: {horizon_years} years
- Sector preferences: {sectors}
- Constraints: {constraints}
- Existing holdings: {holdings}

RULES:
1. Pick diversified tickers across relevant sectors
2. Match risk tolerance: conservative = blue chips/dividends, aggressive = growth/tech
3. Respect constraints (exclusions)
4. Don't duplicate existing holdings unless rebalancing makes sense
5. Include a mix of large-cap stability and growth potential
6. Consider the time horizon: shorter = more stable, longer = more growth

Respond with ONLY a JSON array of ticker symbols, nothing else:
["AAPL", "MSFT", "GOOGL"]"""


def research_agent(state: AgentState) -> dict:
    """
    Select tickers and research them.
    Returns updated state with research results.
    """
    profile = state["investment_profile"]
    
    # Step 1: Ask Claude to pick tickers
    print("\n🔍 Research Agent: Selecting tickers...")
    tickers = _select_tickers(profile)
    print(f"   Selected: {', '.join(tickers)}")
    
    # Step 2: Run research pipeline on each ticker (parallel, with cache)
    print(f"\n📊 Researching {len(tickers)} tickers...")
    
    # Try to get memory from app state for caching
    memory = None
    try:
        from db.memory import Memory
        memory = Memory()
    except Exception:
        pass
    
    pipeline = ResearchPipeline(memory=memory)
    research_results = pipeline.research_multiple(tickers)
    
    # Step 3: Get market caps — reuse pipeline's cached MarketData
    print("\n💰 Fetching market caps...")
    researched_tickers = [r["ticker"] for r in research_results]
    market_caps = pipeline.market.get_multiple_market_caps(researched_tickers)
    
    # Step 4: Compute covariance matrix
    print("\n📐 Computing covariance matrix...")
    cov = pipeline.market.get_covariance_matrix(researched_tickers)
    
    # Build summary message for the user
    summary = _build_research_summary(research_results)
    
    return {
        "messages": [{"role": "assistant", "content": summary}],
        "tickers": researched_tickers,
        "research_results": research_results,
        "market_caps": market_caps,
        "covariance_matrix": cov,
        "current_agent": "strategy",
    }


def _select_tickers(profile: dict) -> list[str]:
    """Use Claude to select appropriate tickers for the profile."""
    prompt = TICKER_SELECTION_PROMPT.format(
        capital=profile["capital"],
        risk_category=profile.get("risk_category", "moderate"),
        risk_tolerance=profile["risk_tolerance"],
        horizon_years=profile["horizon_years"],
        sectors=", ".join(profile.get("sector_preferences", [])) or "no preference",
        constraints=", ".join(profile.get("constraints", [])) or "none",
        holdings=json.dumps(profile.get("existing_holdings", {})) or "none",
    )
    
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    
    raw = response.content[0].text.strip()
    
    # Clean potential markdown
    if "```" in raw:
        raw = raw.split("```")[1].split("```")[0].strip()
        if raw.startswith("json"):
            raw = raw[4:].strip()
    
    try:
        tickers = json.loads(raw)
        if isinstance(tickers, list):
            return [t.upper() for t in tickers[:8]]  # Cap at 8
    except json.JSONDecodeError:
        pass
    
    # Fallback: sensible defaults
    print("   ⚠️ Falling back to default tickers")
    return ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]


def _build_research_summary(results: list[dict]) -> str:
    """Build a user-friendly research summary."""
    lines = ["Here's what I found:\n"]
    
    for r in results:
        name = r.get("company_name") or r["ticker"]
        price = r["current_price"]
        
        # Sentiment emoji
        sent_score = r.get("sentiment", {}).get("score", 0)
        if sent_score >= 0.3:
            emoji = "🟢"
        elif sent_score <= -0.3:
            emoji = "🔴"
        else:
            emoji = "🟡"
        
        # RSI signal
        rsi = r.get("technicals", {}).get("rsi_14")
        rsi_text = ""
        if rsi:
            if rsi < 30:
                rsi_text = " (oversold)"
            elif rsi > 70:
                rsi_text = " (overbought)"
        
        # Fundamentals
        pe = r.get("fundamentals", {}).get("pe_ratio")
        pe_text = f", P/E {pe:.1f}" if pe else ""
        
        sector = r.get("fundamentals", {}).get("sector", "")
        sector_text = f" [{sector}]" if sector else ""
        
        lines.append(
            f"{emoji} **{name}** ({r['ticker']}) — ${price:.2f}{pe_text}{sector_text}{rsi_text}"
        )
    
    lines.append("\nNow building your optimized portfolio allocation...")
    return "\n".join(lines)