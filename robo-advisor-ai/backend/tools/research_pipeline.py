"""
RoboAdvisor AI — Research Pipeline
Orchestrates market data, technicals, and sentiment into a complete AssetResearch.
Parallelizes multi-ticker research via ThreadPoolExecutor.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from tools.market_data import MarketData
from tools.technicals import TechnicalAnalysis
from tools.sentiment import SentimentAnalyzer
from typing import Optional, Callable


class ResearchPipeline:
    """Run full research on a ticker: price + fundamentals + technicals + sentiment."""
    
    def __init__(self, on_status: Optional[Callable[[str], None]] = None, memory=None):
        self.market = MarketData()
        self.sentiment = SentimentAnalyzer()
        self.on_status = on_status  # Callback for streaming status updates
        self.memory = memory  # Optional Supabase memory for caching
    
    def _emit(self, msg: str):
        """Send a status update if callback is set."""
        print(f"  {msg}")
        if self.on_status:
            self.on_status(msg)
    
    def research_ticker(self, ticker: str) -> Optional[dict]:
        """
        Full research on a single ticker.
        Returns a dict matching the AssetResearch model.
        Checks Supabase cache first if memory is available.
        """
        ticker = ticker.upper()
        
        # Check cache first
        if self.memory:
            try:
                cached = self.memory.get_cached_research(ticker, max_age_hours=1)
                if cached:
                    self._emit(f"⚡ {ticker} loaded from cache")
                    return {
                        "ticker": ticker,
                        "company_name": cached.get("company_name"),
                        "current_price": cached["current_price"],
                        "currency": "USD",
                        "technicals": cached.get("technicals", {}),
                        "fundamentals": cached.get("fundamentals", {}),
                        "sentiment": cached.get("sentiment", {}),
                    }
            except Exception:
                pass  # Cache miss, research fresh
        
        self._emit(f"📊 Researching {ticker}...")
        
        # 1. Current price + company name + fundamentals (all from cached .info)
        price = self.market.get_current_price(ticker)
        if price is None:
            self._emit(f"❌ Could not fetch price for {ticker}")
            return None
        
        company_name = self.market.get_company_name(ticker)
        fundamentals = self.market.get_fundamentals(ticker)
        
        # 2. Historical prices for technicals
        history = self.market.get_historical_prices(ticker, period="1y")
        
        # 3. Technical indicators
        technicals = {}
        if history and history["close"]:
            ta = TechnicalAnalysis(history["close"])
            technicals = ta.all_indicators()
        
        # 4. News sentiment via Claude
        sentiment = self.sentiment.analyze(ticker, company_name)
        
        self._emit(f"✅ {ticker} complete (${price:.2f})")
        
        result = {
            "ticker": ticker,
            "company_name": company_name,
            "current_price": price,
            "currency": "USD",
            "technicals": technicals,
            "fundamentals": fundamentals,
            "sentiment": sentiment,
        }
        
        # Save to cache
        if self.memory:
            try:
                self.memory.save_research(ticker, result)
            except Exception:
                pass  # Don't fail if cache write fails
        
        return result
    
    def research_multiple(self, tickers: list[str], max_workers: int = 4) -> list[dict]:
        """Research multiple tickers in parallel."""
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_ticker = {
                executor.submit(self.research_ticker, t): t
                for t in tickers
            }
            
            for future in as_completed(future_to_ticker):
                ticker = future_to_ticker[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                except Exception as e:
                    self._emit(f"❌ Error researching {ticker}: {e}")
        
        # Sort by original ticker order
        ticker_order = {t.upper(): i for i, t in enumerate(tickers)}
        results.sort(key=lambda r: ticker_order.get(r["ticker"], 999))
        
        return results