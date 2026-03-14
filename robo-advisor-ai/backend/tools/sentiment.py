"""
RoboAdvisor AI — Sentiment Analysis Tool
Fetches recent news (NewsAPI) and scores sentiment via Claude.
"""

import os
import json
import requests
import anthropic
from typing import Optional


class SentimentAnalyzer:
    """Fetch news and score sentiment using Claude."""
    
    def __init__(self):
        self.news_key = os.getenv("NEWS_API_KEY")
        self.news_base = "https://newsapi.org/v2"
        self.claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    def fetch_news(self, query: str, max_articles: int = 5) -> list[dict]:
        """
        Fetch recent news articles from NewsAPI.
        Returns list of {title, description, source, url, publishedAt}.
        """
        if not self.news_key:
            print("Warning: NEWS_API_KEY not set")
            return []
        
        try:
            resp = requests.get(
                f"{self.news_base}/everything",
                params={
                    "q": query,
                    "sortBy": "publishedAt",
                    "pageSize": max_articles,
                    "language": "en",
                    "apiKey": self.news_key,
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            
            articles = []
            for a in data.get("articles", []):
                articles.append({
                    "title": a.get("title", ""),
                    "description": a.get("description", ""),
                    "source": a.get("source", {}).get("name", ""),
                    "url": a.get("url", ""),
                    "publishedAt": a.get("publishedAt", ""),
                })
            return articles
            
        except Exception as e:
            print(f"NewsAPI error: {e}")
            return []
    
    def score_sentiment(self, ticker: str, articles: list[dict]) -> dict:
        """
        Use Claude to analyze news sentiment for a ticker.
        Returns {score: float, summary: str, num_articles: int, top_headlines: list}.
        """
        if not articles:
            return {
                "score": 0.0,
                "summary": "No recent news found.",
                "num_articles": 0,
                "top_headlines": [],
            }
        
        # Build the news context for Claude
        news_text = ""
        headlines = []
        for i, a in enumerate(articles, 1):
            news_text += f"\n{i}. [{a['source']}] {a['title']}\n   {a['description']}\n"
            headlines.append(a["title"])
        
        prompt = f"""Analyze the following recent news articles about {ticker} and provide:
1. A sentiment score from -1.0 (very bearish) to 1.0 (very bullish)
2. A 2-3 sentence summary of the overall sentiment

News articles:
{news_text}

Respond in this exact JSON format only, no other text:
{{"score": <float>, "summary": "<string>"}}"""
        
        try:
            response = self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}],
            )
            
            raw = response.content[0].text.strip()
            # Clean potential markdown wrapping
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            
            result = json.loads(raw)
            
            return {
                "score": max(-1.0, min(1.0, float(result["score"]))),
                "summary": result["summary"],
                "num_articles": len(articles),
                "top_headlines": headlines[:3],
            }
            
        except Exception as e:
            print(f"Claude sentiment error: {e}")
            return {
                "score": 0.0,
                "summary": f"Error analyzing sentiment: {str(e)}",
                "num_articles": len(articles),
                "top_headlines": headlines[:3],
            }
    
    def analyze(self, ticker: str, company_name: Optional[str] = None) -> dict:
        """
        Full pipeline: fetch news → score with Claude.
        """
        query = f"{ticker} stock"
        if company_name:
            query = f"{company_name} {ticker} stock"
        
        articles = self.fetch_news(query)
        return self.score_sentiment(ticker, articles)
