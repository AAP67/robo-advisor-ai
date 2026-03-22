"""
RoboAdvisor AI — Market Data Tool
Fetches prices (yfinance) and fundamentals.
Uses an in-memory cache so .info is only called once per ticker per session.
"""

import yfinance as yf
from typing import Optional


class MarketData:
    """Fetch price data and fundamentals for stocks."""
    
    def __init__(self):
        self._info_cache: dict[str, dict] = {}
        self._ticker_cache: dict[str, yf.Ticker] = {}
    
    def _get_ticker(self, ticker: str) -> yf.Ticker:
        """Get or create a yf.Ticker instance (reused for .history calls)."""
        ticker = ticker.upper()
        if ticker not in self._ticker_cache:
            self._ticker_cache[ticker] = yf.Ticker(ticker)
        return self._ticker_cache[ticker]
    
    def _get_info(self, ticker: str) -> dict:
        """Get .info for a ticker, cached. This is the expensive call — only do it once."""
        ticker = ticker.upper()
        if ticker not in self._info_cache:
            try:
                stock = self._get_ticker(ticker)
                self._info_cache[ticker] = stock.info or {}
            except Exception as e:
                print(f"Error fetching info for {ticker}: {e}")
                self._info_cache[ticker] = {}
        return self._info_cache[ticker]
    
    # ── Price Data ──
    
    def get_current_price(self, ticker: str) -> Optional[float]:
        """Get the latest price for a ticker."""
        try:
            info = self._get_info(ticker)
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
            stock = self._get_ticker(ticker)
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
            info = self._get_info(ticker)
            return info.get("marketCap")
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
    
    # ── Fundamentals ──
    
    def get_fundamentals(self, ticker: str) -> dict:
        """
        Get key fundamental metrics.
        Returns a flat dict matching our Fundamentals model.
        """
        info = self._get_info(ticker)
        
        return {
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "price_to_book": info.get("priceToBook"),
            "revenue_growth_yoy": info.get("revenueGrowth"),
            "profit_margin": info.get("profitMargins"),
            "roe": info.get("returnOnEquity"),
            "debt_to_equity": info.get("debtToEquity"),
            "dividend_yield": info.get("dividendYield"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
        }
    
    def get_company_name(self, ticker: str) -> Optional[str]:
        """Get company name."""
        try:
            info = self._get_info(ticker)
            return info.get("longName") or info.get("shortName")
        except Exception:
            return None