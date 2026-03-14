"""
RoboAdvisor AI — Research Pipeline
Orchestrates market data, technicals, and sentiment into a complete AssetResearch.
"""

from tools.market_data import MarketData
from tools.technicals import TechnicalAnalysis
from tools.sentiment import SentimentAnalyzer
from typing import Optional


class ResearchPipeline:
    """Run full research on a ticker: price + fundamentals + technicals + sentiment."""
    
    def __init__(self):
        self.market = MarketData()
        self.sentiment = SentimentAnalyzer()
    
    def research_ticker(self, ticker: str) -> Optional[dict]:
        """
        Full research on a single ticker.
        Returns a dict matching the AssetResearch model.
        """
        ticker = ticker.upper()
        print(f"  📊 Researching {ticker}...")
        
        # 1. Current price
        print(f"    → Fetching price...")
        price = self.market.get_current_price(ticker)
        if price is None:
            print(f"    ❌ Could not fetch price for {ticker}")
            return None
        
        # 2. Company name
        company_name = self.market.get_company_name(ticker)
        
        # 3. Historical prices for technicals
        print(f"    → Fetching historical data...")
        history = self.market.get_historical_prices(ticker, period="1y")
        
        # 4. Technical indicators
        technicals = {}
        if history and history["close"]:
            print(f"    → Computing technicals...")
            ta = TechnicalAnalysis(history["close"])
            technicals = ta.all_indicators()
        
        # 5. Fundamentals from FMP
        print(f"    → Fetching fundamentals...")
        fundamentals = self.market.get_fundamentals(ticker)
        
        # 6. News sentiment via Claude
        print(f"    → Analyzing sentiment...")
        sentiment = self.sentiment.analyze(ticker, company_name)
        
        print(f"    ✅ {ticker} complete (${price:.2f})")
        
        return {
            "ticker": ticker,
            "company_name": company_name,
            "current_price": price,
            "currency": "USD",
            "technicals": technicals,
            "fundamentals": fundamentals,
            "sentiment": sentiment,
        }
    
    def research_multiple(self, tickers: list[str]) -> list[dict]:
        """Research multiple tickers."""
        results = []
        for ticker in tickers:
            result = self.research_ticker(ticker)
            if result:
                results.append(result)
        return results
