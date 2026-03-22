"""
RoboAdvisor AI — Strategy Agent
Generates market views via Claude, runs Black-Litterman optimizer,
and presents the final portfolio allocation.
"""

import os
import json
import numpy as np
import anthropic
from agents.state import AgentState
from optimizer.black_litterman import BlackLittermanOptimizer, BLView
from status import emit_status


client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

VIEWS_PROMPT = """You are a quantitative portfolio strategist. Based on the research below, generate expected return views for each asset to feed into a Black-Litterman portfolio optimizer.

Investment Profile:
- Risk tolerance: {risk_category} ({risk_tolerance}/10)
- Time horizon: {horizon_years} years

Research Data:
{research_summary}

For EACH ticker, provide:
1. expected_annual_return: Your expected 1-year return (e.g., 0.12 = 12%). Consider fundamentals, technicals, and sentiment.
2. confidence: How confident you are in this view (0.1 to 0.9). Higher = stronger conviction.

GUIDELINES:
- Conservative risk tolerance → favor stable returns, lower expected returns
- Aggressive risk tolerance → allow higher expected returns
- RSI < 30 (oversold) → potentially higher expected return
- RSI > 70 (overbought) → potentially lower expected return
- Strong positive sentiment + good fundamentals → higher confidence
- Mixed signals → lower confidence
- Typical range for expected returns: -0.10 to 0.30

Respond with ONLY a JSON array, no other text:
[{{"ticker": "AAPL", "expected_annual_return": 0.12, "confidence": 0.7}}]"""


def strategy_agent(state: AgentState) -> dict:
    """
    Generate Claude views → run Black-Litterman → present allocation.
    """
    profile = state["investment_profile"]
    research = state["research_results"]
    market_caps = state["market_caps"]
    cov_data = state["covariance_matrix"]
    
    if not research:
        return {
            "messages": [{"role": "assistant", "content": "I couldn't research any tickers. Please try different preferences."}],
            "current_agent": "done",
            "error": "No research results",
        }
    
    # Step 1: Generate views via Claude
    emit_status("🧠 Generating market views via Claude...")
    views_data = _generate_views(profile, research)
    emit_status(f"📊 Generated {len(views_data)} market views")
    
    # Step 2: Prepare optimizer inputs
    # Only use tickers we have both research AND market cap for
    valid_tickers = [r["ticker"] for r in research if r["ticker"] in market_caps]
    
    if len(valid_tickers) < 2:
        return {
            "messages": [{"role": "assistant", "content": "Not enough valid tickers for optimization. Please try again."}],
            "current_agent": "done",
            "error": "Insufficient data for optimization",
        }
    
    # Align everything to valid_tickers order
    caps = [market_caps[t] for t in valid_tickers]
    
    # Build covariance matrix
    if cov_data and cov_data.get("matrix"):
        cov_tickers = cov_data["tickers"]
        cov_matrix = np.array(cov_data["matrix"])
        
        # Reorder to match valid_tickers
        indices = []
        final_tickers = []
        for t in valid_tickers:
            if t in cov_tickers:
                indices.append(cov_tickers.index(t))
                final_tickers.append(t)
        
        if len(final_tickers) < 2:
            return {
                "messages": [{"role": "assistant", "content": "Could not align covariance data. Please try again."}],
                "current_agent": "done",
                "error": "Covariance alignment failed",
            }
        
        cov_aligned = cov_matrix[np.ix_(indices, indices)]
        caps_aligned = [market_caps[t] for t in final_tickers]
    else:
        return {
            "messages": [{"role": "assistant", "content": "Could not compute covariance matrix. Please try again."}],
            "current_agent": "done",
            "error": "No covariance matrix",
        }
    
    # Step 3: Build BL views
    bl_views = []
    for v in views_data:
        ticker = v["ticker"]
        if ticker in final_tickers:
            idx = final_tickers.index(ticker)
            bl_views.append(BLView(
                asset_index=idx,
                expected_return=v["expected_annual_return"],
                confidence=v["confidence"],
            ))
    
    if not bl_views:
        # No views matched — use equilibrium (market cap) weights
        emit_status("⚠️ No views matched, using market-cap weights")
    
    # Step 4: Run Black-Litterman
    emit_status("📈 Running Black-Litterman optimization...")
    
    # Risk aversion based on profile
    risk_aversion = _risk_to_aversion(profile["risk_tolerance"])
    
    optimizer = BlackLittermanOptimizer(
        tickers=final_tickers,
        market_caps=caps_aligned,
        covariance_matrix=cov_aligned,
        risk_free_rate=0.045,
    )
    
    if bl_views:
        result = optimizer.optimize(bl_views, tau=0.05, risk_aversion=risk_aversion)
    else:
        result = optimizer.optimize_no_views(risk_aversion=risk_aversion)
    
    # Step 5: Build strategy output
    research_lookup = {r["ticker"]: r for r in research}
    allocations = []
    risk_contribs = {}
    for i, (ticker, weight) in enumerate(zip(result.tickers, result.weights)):
        r = research_lookup.get(ticker, {})
        dollar_amount = weight * profile["capital"]
        price = r.get("current_price", 0)
        shares = int(dollar_amount / price) if price > 0 else 0
        
        # Find the view rationale
        view = next((v for v in views_data if v["ticker"] == ticker), {})
        
        # Risk contribution
        rc = float(result.risk_contributions[i]) if i < len(result.risk_contributions) else 0.0
        risk_contribs[ticker] = round(rc, 4)
        
        allocations.append({
            "ticker": ticker,
            "company_name": r.get("company_name"),
            "weight": round(float(weight), 4),
            "shares": shares,
            "dollar_amount": round(dollar_amount, 2),
            "rationale": view.get("rationale", "Market-cap weighted allocation"),
            "risk_contribution": round(rc, 4),
        })
    
    strategy = {
        "allocations": allocations,
        "expected_annual_return": result.portfolio_return,
        "expected_volatility": result.portfolio_volatility,
        "sharpe_ratio": result.sharpe_ratio,
        "risk_contributions": risk_contribs,
        "bl_params": {
            "tau": 0.05,
            "risk_aversion": risk_aversion,
            "view_confidences": {v["ticker"]: v["confidence"] for v in views_data},
        },
        "tickers_researched": final_tickers,
        "reasoning": "",  # Will be filled by the presentation
    }
    
    # Step 6: Generate reasoning via Claude
    emit_status("💬 Generating strategy explanation...")
    reasoning = _generate_reasoning(profile, strategy, research)
    strategy["reasoning"] = reasoning
    
    # Step 7: Build presentation
    presentation = _present_strategy(profile, strategy)
    
    return {
        "messages": [{"role": "assistant", "content": presentation}],
        "strategy": strategy,
        "current_agent": "done",
    }


def _generate_views(profile: dict, research: list[dict]) -> list[dict]:
    """Ask Claude to generate expected return views from research data."""
    
    # Build research summary for the prompt
    summaries = []
    for r in research:
        s = r.get("sentiment", {})
        t = r.get("technicals", {})
        f = r.get("fundamentals", {})
        
        summaries.append(
            f"**{r['ticker']}** ({r.get('company_name', 'N/A')})\n"
            f"  Price: ${r['current_price']:.2f}\n"
            f"  P/E: {f.get('pe_ratio', 'N/A')}, Rev Growth: {f.get('revenue_growth_yoy', 'N/A')}\n"
            f"  RSI: {t.get('rsi_14', 'N/A')}, MACD: {t.get('macd', 'N/A')}\n"
            f"  Sentiment: {s.get('score', 0)} — {s.get('summary', 'N/A')}"
        )
    
    prompt = VIEWS_PROMPT.format(
        risk_category=profile.get("risk_category", "moderate"),
        risk_tolerance=profile["risk_tolerance"],
        horizon_years=profile["horizon_years"],
        research_summary="\n\n".join(summaries),
    )
    
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    
    raw = response.content[0].text.strip()
    
    # Clean markdown
    if "```" in raw:
        raw = raw.split("```")[1].split("```")[0].strip()
        if raw.startswith("json"):
            raw = raw[4:].strip()
    
    try:
        views = json.loads(raw)
        if isinstance(views, list):
            return views
    except json.JSONDecodeError:
        emit_status(f"⚠️ Could not parse views, using defaults")
    
    return []


def _generate_reasoning(profile: dict, strategy: dict, research: list[dict]) -> str:
    """Ask Claude to explain the strategy in plain English."""
    
    alloc_text = "\n".join(
        f"  {a['ticker']}: {a['weight']:.1%} (${a['dollar_amount']:,.0f})"
        for a in strategy["allocations"]
    )
    
    prompt = f"""You just built a portfolio for an investor. Explain your reasoning in 3-4 sentences. Be specific about why you chose these weights.

Profile: ${profile['capital']:,.0f}, risk {profile['risk_tolerance']}/10, {profile['horizon_years']}-year horizon
Sectors: {', '.join(profile.get('sector_preferences', []))}

Allocation:
{alloc_text}

Expected return: {strategy['expected_annual_return']:.1%}
Sharpe ratio: {strategy['sharpe_ratio']:.2f}

Keep it concise and confident. No disclaimers."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    
    return response.content[0].text.strip()


def _present_strategy(profile: dict, strategy: dict) -> str:
    """Format the strategy as a user-friendly message."""
    lines = ["Here's your optimized portfolio:\n"]
    
    for a in sorted(strategy["allocations"], key=lambda x: x["weight"], reverse=True):
        name = a.get("company_name") or a["ticker"]
        bar = "█" * int(a["weight"] * 30)
        lines.append(
            f"**{name}** ({a['ticker']}): {a['weight']:.1%} — "
            f"${a['dollar_amount']:,.0f} (~{a['shares']} shares)\n"
            f"  {bar}"
        )
    
    lines.append(f"\n📊 **Portfolio Stats**")
    lines.append(f"• Expected annual return: {strategy['expected_annual_return']:.1%}")
    lines.append(f"• Expected volatility: {strategy['expected_volatility']:.1%}")
    lines.append(f"• Sharpe ratio: {strategy['sharpe_ratio']:.2f}")
    
    # Risk decomposition
    risk_contribs = strategy.get("risk_contributions", {})
    if risk_contribs:
        lines.append(f"\n⚠️ **Risk Decomposition**")
        for ticker, rc in sorted(risk_contribs.items(), key=lambda x: x[1], reverse=True):
            if rc > 0.01:
                lines.append(f"• {ticker}: {rc:.1%} of portfolio risk")
    
    lines.append(f"\n💡 **Strategy**\n{strategy['reasoning']}")
    
    return "\n".join(lines)


def _risk_to_aversion(risk_tolerance: int) -> float:
    """Convert 1-10 risk tolerance to Black-Litterman risk aversion parameter.
    Higher risk tolerance → lower risk aversion."""
    # Risk aversion typically ranges from 1.0 (aggressive) to 5.0 (conservative)
    return 5.5 - (risk_tolerance * 0.4)