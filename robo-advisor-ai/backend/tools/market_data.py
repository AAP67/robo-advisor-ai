"""
RoboAdvisor AI — Market Data Tool
Fetches prices (yfinance) and fundamentals (Financial Modeling Prep).
"""

import yfinance as yf
from typing import Optional


class MarketData:
    """Fetch price data and fundamentals for stocks."""
    
    def __init__(self):
        pass
    
    # ── Price Data (yfinance) ──
    
    def get_current_price(self, ticker: str) -> Optional[float]:
        """Get the latest price for a ticker."""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            # Try multiple fields, yfinance can be inconsistent
            price = (
                info.get("currentPrice")
                or info.get("regularMarketPrice")
                or info.get("previousClose")
            )
            return float(price) if price else None
        except Exception as e:
            print(f"Error fetching price for {ticker}: {e}")
            return None
    
    def get_historical_prices(
        self, ticker: str, period: str = "1y", interval: str = "1d"
    ) -> Optional[dict]:
        """
        Get historical price data.
        period: 1mo, 3mo, 6mo, 1y, 2y, 5y
        interval: 1d, 1wk, 1mo
        Returns dict with 'dates', 'close', 'volume' lists.
        """
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period=period, interval=interval)
            
            if hist.empty:
                return None
            
            return {
                "dates": [d.strftime("%Y-%m-%d") for d in hist.index],
                "open": hist["Open"].tolist(),
                "high": hist["High"].tolist(),
                "low": hist["Low"].tolist(),
                "close": hist["Close"].tolist(),
                "volume": hist["Volume"].tolist(),
            }
        except Exception as e:
            print(f"Error fetching history for {ticker}: {e}")
            return None
    
    def get_market_cap(self, ticker: str) -> Optional[float]:
        """Get market cap for a ticker."""
        try:
            stock = yf.Ticker(ticker)
            return stock.info.get("marketCap")
        except Exception:
            return None
    
    def get_multiple_market_caps(self, tickers: list[str]) -> dict[str, float]:
        """Get market caps for multiple tickers."""
        caps = {}
        for t in tickers:
            cap = self.get_market_cap(t)
            if cap:
                caps[t] = cap
        return caps
    
    def get_covariance_matrix(
        self, tickers: list[str], period: str = "1y"
    ) -> Optional[dict]:
        """
        Compute annualized covariance matrix from historical daily returns.
        Returns dict with 'matrix' (list of lists) and 'tickers'.
        """
        import numpy as np
        
        try:
            # Download all at once for alignment
            data = yf.download(tickers, period=period, interval="1d", progress=False)
            
            if data.empty:
                return None
            
            # Get close prices
            if len(tickers) == 1:
                close = data["Close"].to_frame(tickers[0])
            else:
                close = data["Close"]
            
            # Daily returns
            returns = close.pct_change().dropna()
            
            # Annualized covariance (252 trading days)
            cov_matrix = returns.cov() * 252
            
            return {
                "matrix": cov_matrix.values.tolist(),
                "tickers": list(cov_matrix.columns),
            }
        except Exception as e:
            print(f"Error computing covariance: {e}")
            return None
    
    # ── Fundamentals (yfinance) ──
    
    def get_fundamentals(self, ticker: str) -> dict:
        """
        Get key fundamental metrics from yfinance.
        Returns a flat dict matching our Fundamentals model.
        """
        result = {
            "market_cap": None,
            "pe_ratio": None,
            "forward_pe": None,
            "price_to_book": None,
            "revenue_growth_yoy": None,
            "profit_margin": None,
            "roe": None,
            "debt_to_equity": None,
            "dividend_yield": None,
            "sector": None,
            "industry": None,
        }
        
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            result["market_cap"] = info.get("marketCap")
            result["pe_ratio"] = info.get("trailingPE")
            result["forward_pe"] = info.get("forwardPE")
            result["price_to_book"] = info.get("priceToBook")
            result["profit_margin"] = info.get("profitMargins")
            result["roe"] = info.get("returnOnEquity")
            result["debt_to_equity"] = info.get("debtToEquity")
            result["dividend_yield"] = info.get("dividendYield")
            result["sector"] = info.get("sector")
            result["industry"] = info.get("industry")
            
            # Revenue growth: compare last two annual revenues
            rev_growth = info.get("revenueGrowth")
            if rev_growth is not None:
                result["revenue_growth_yoy"] = rev_growth
            
        except Exception as e:
            print(f"yfinance fundamentals error for {ticker}: {e}")
        
        return result
    
    def get_company_name(self, ticker: str) -> Optional[str]:
        """Get company name from yfinance."""
        try:
            stock = yf.Ticker(ticker)
            return stock.info.get("longName") or stock.info.get("shortName")
        except Exception:
            return None
