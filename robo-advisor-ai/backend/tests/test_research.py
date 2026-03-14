"""
Test the research pipeline with real data.
Run: cd backend && python -m tests.test_research

Requires: ANTHROPIC_API_KEY, FMP_API_KEY, NEWS_API_KEY in .env
Uses real API calls — will count against your free tier limits.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from tools.research_pipeline import ResearchPipeline


def test_single_ticker():
    """Research AAPL end-to-end."""
    pipeline = ResearchPipeline()
    
    print("=" * 60)
    print("RESEARCHING AAPL")
    print("=" * 60)
    
    result = pipeline.research_ticker("AAPL")
    
    assert result is not None, "Research should return data"
    assert result["ticker"] == "AAPL"
    assert result["current_price"] > 0
    
    # Print results
    print(f"\n{'─' * 40}")
    print(f"Company:  {result['company_name']}")
    print(f"Price:    ${result['current_price']:.2f}")
    
    t = result["technicals"]
    print(f"\nTechnicals:")
    print(f"  RSI(14):   {t.get('rsi_14')}")
    print(f"  MACD:      {t.get('macd')}")
    print(f"  SMA(50):   ${t.get('sma_50')}")
    print(f"  SMA(200):  ${t.get('sma_200')}")
    print(f"  Bollinger: {t.get('bollinger_lower')} — {t.get('bollinger_mid')} — {t.get('bollinger_upper')}")
    
    f = result["fundamentals"]
    print(f"\nFundamentals:")
    print(f"  P/E:             {f.get('pe_ratio')}")
    print(f"  Revenue Growth:  {f.get('revenue_growth_yoy')}")
    print(f"  Profit Margin:   {f.get('profit_margin')}")
    print(f"  ROE:             {f.get('roe')}")
    print(f"  Debt/Equity:     {f.get('debt_to_equity')}")
    print(f"  Sector:          {f.get('sector')}")
    
    s = result["sentiment"]
    print(f"\nSentiment (Claude):")
    print(f"  Score:    {s['score']} ({_score_label(s['score'])})")
    print(f"  Summary:  {s['summary']}")
    print(f"  Articles: {s['num_articles']}")
    for h in s.get("top_headlines", []):
        print(f"    • {h[:80]}")
    
    print(f"\n✅ AAPL research complete!")
    return result


def test_covariance():
    """Test covariance matrix computation."""
    from tools.market_data import MarketData
    
    md = MarketData()
    tickers = ["AAPL", "MSFT", "GOOGL"]
    
    print(f"\n{'=' * 60}")
    print(f"COVARIANCE MATRIX: {', '.join(tickers)}")
    print(f"{'=' * 60}")
    
    cov = md.get_covariance_matrix(tickers)
    
    assert cov is not None, "Should return covariance data"
    assert len(cov["matrix"]) == 3
    assert len(cov["matrix"][0]) == 3
    
    import numpy as np
    matrix = np.array(cov["matrix"])
    
    for i, t in enumerate(cov["tickers"]):
        row = " ".join(f"{matrix[i][j]:8.4f}" for j in range(len(tickers)))
        print(f"  {t:6s}: {row}")
    
    print(f"\n✅ Covariance matrix computed!")
    return cov


def _score_label(score: float) -> str:
    if score >= 0.5: return "bullish"
    if score >= 0.1: return "slightly bullish"
    if score >= -0.1: return "neutral"
    if score >= -0.5: return "slightly bearish"
    return "bearish"


if __name__ == "__main__":
    result = test_single_ticker()
    cov = test_covariance()
    print(f"\n🎉 Step 3 complete! All market data tools working.")
