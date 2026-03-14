"""
Test the Black-Litterman optimizer with sample data.
Run: python -m tests.test_optimizer
"""

import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from optimizer.black_litterman import BlackLittermanOptimizer, BLView


def test_basic_optimization():
    """4-stock portfolio with 2 Claude-generated views."""
    
    tickers = ["AAPL", "GOOGL", "MSFT", "AMZN"]
    
    # Market caps (approximate, in USD)
    market_caps = [3.0e12, 2.0e12, 2.8e12, 1.9e12]
    
    # Sample annualized covariance matrix (realistic-ish)
    # In production, this comes from yfinance historical returns
    covariance = np.array([
        [0.0576, 0.0270, 0.0324, 0.0297],  # AAPL
        [0.0270, 0.0625, 0.0300, 0.0350],  # GOOGL
        [0.0324, 0.0300, 0.0529, 0.0280],  # MSFT
        [0.0297, 0.0350, 0.0280, 0.0676],  # AMZN
    ])
    
    optimizer = BlackLittermanOptimizer(
        tickers=tickers,
        market_caps=market_caps,
        covariance_matrix=covariance,
        risk_free_rate=0.045,
    )
    
    # Simulate Claude's views:
    # - Bullish on AAPL (15% expected return, high confidence)
    # - Bearish on AMZN (3% expected return, moderate confidence)
    views = [
        BLView(asset_index=0, expected_return=0.15, confidence=0.8),
        BLView(asset_index=3, expected_return=0.03, confidence=0.5),
    ]
    
    result = optimizer.optimize(views, tau=0.05, risk_aversion=2.5)
    
    print("=" * 60)
    print("BLACK-LITTERMAN OPTIMIZATION RESULT")
    print("=" * 60)
    print(f"\nViews applied:")
    print(f"  - AAPL: 15% expected return (confidence: 80%)")
    print(f"  - AMZN: 3% expected return (confidence: 50%)")
    print(f"\nOptimal Allocation:")
    for ticker, weight in zip(result.tickers, result.weights):
        bar = "█" * int(weight * 40)
        print(f"  {ticker:6s}: {weight:6.1%}  {bar}")
    print(f"\nPortfolio Stats:")
    print(f"  Expected Return:    {result.portfolio_return:.2%}")
    print(f"  Expected Volatility: {result.portfolio_volatility:.2%}")
    print(f"  Sharpe Ratio:       {result.sharpe_ratio:.2f}")
    
    # Basic sanity checks
    assert abs(sum(result.weights) - 1.0) < 1e-6, "Weights must sum to 1"
    assert all(w >= 0 for w in result.weights), "No short positions (long-only)"
    assert result.sharpe_ratio > 0, "Sharpe should be positive with these views"
    
    # AAPL should have highest weight (bullish view)
    aapl_weight = result.weights[0]
    amzn_weight = result.weights[3]
    assert aapl_weight > amzn_weight, "AAPL (bullish) should outweigh AMZN (bearish)"
    
    print("\n✅ All assertions passed!")
    print(f"\nFull result dict:\n{result.to_dict()}")
    return result


def test_no_views():
    """Fallback: market-cap weighted portfolio."""
    
    tickers = ["AAPL", "GOOGL", "MSFT"]
    market_caps = [3.0e12, 2.0e12, 2.8e12]
    
    covariance = np.array([
        [0.0576, 0.0270, 0.0324],
        [0.0270, 0.0625, 0.0300],
        [0.0324, 0.0300, 0.0529],
    ])
    
    optimizer = BlackLittermanOptimizer(
        tickers=tickers,
        market_caps=market_caps,
        covariance_matrix=covariance,
    )
    
    result = optimizer.optimize_no_views()
    
    print("\n" + "=" * 60)
    print("NO VIEWS (MARKET CAP WEIGHTED)")
    print("=" * 60)
    for ticker, weight in zip(result.tickers, result.weights):
        print(f"  {ticker:6s}: {weight:6.1%}")
    
    # Should be roughly proportional to market caps
    assert result.weights[0] > result.weights[1], "AAPL > GOOGL by market cap"
    print("\n✅ No-views test passed!")
    return result


if __name__ == "__main__":
    test_basic_optimization()
    test_no_views()
    print("\n🎉 All tests passed! Step 1 complete.")
