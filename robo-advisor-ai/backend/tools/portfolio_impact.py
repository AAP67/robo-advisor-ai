"""
RoboAdvisor AI — Portfolio Import
Accepts CSV, image (screenshot), or PDF uploads.
Extracts holdings as structured data.
"""

import os
import io
import csv
import json
import base64
import anthropic
from fastapi import APIRouter, UploadFile, File, HTTPException
from status import emit_status


router = APIRouter()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

EXTRACT_PROMPT = """You are extracting stock portfolio holdings from an uploaded document.

Extract each position as a JSON array. Each item must have:
- "ticker": stock ticker symbol (uppercase)
- "shares": number of shares held (float)
- "value": approximate dollar value if available, otherwise null

If you see a cost basis, use current approximate value if you can infer it, otherwise use cost basis.
If shares aren't shown but dollar values are, set shares to null.
If the document shows mutual funds or ETFs, include them.
Ignore cash balances, totals, and summary rows.

Respond with ONLY a JSON array, no other text:
[{"ticker": "AAPL", "shares": 100, "value": 18520.00}]

If you cannot extract any holdings, respond with: []"""


@router.post("/upload-portfolio")
async def upload_portfolio(file: UploadFile = File(...)):
    """
    Upload a portfolio file (CSV, image, or PDF).
    Returns extracted holdings as structured data.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    content = await file.read()
    filename = file.filename.lower()
    content_type = file.content_type or ""
    
    # Route by file type
    if filename.endswith(".csv") or "csv" in content_type:
        holdings = _parse_csv(content)
    elif filename.endswith(".pdf") or "pdf" in content_type:
        holdings = _extract_with_claude(content, "application/pdf")
    elif any(filename.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp"]):
        media_type = "image/png" if filename.endswith(".png") else "image/jpeg"
        if filename.endswith(".webp"):
            media_type = "image/webp"
        holdings = _extract_with_claude(content, media_type)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {filename}. Supported: CSV, PDF, PNG, JPG"
        )
    
    # Convert to existing_holdings dict for the intake profile
    existing_holdings = {}
    for h in holdings:
        ticker = h.get("ticker", "").upper()
        if ticker:
            value = h.get("value") or 0
            existing_holdings[ticker] = value
    
    return {
        "holdings": holdings,
        "existing_holdings": existing_holdings,
        "count": len(holdings),
        "summary": _build_summary(holdings),
    }


def _parse_csv(content: bytes) -> list[dict]:
    """Parse a CSV file for portfolio holdings."""
    try:
        text = content.decode("utf-8-sig")  # Handle BOM
        reader = csv.DictReader(io.StringIO(text))
        
        holdings = []
        for row in reader:
            # Try common column names
            ticker = (
                row.get("Symbol") or row.get("symbol") or
                row.get("Ticker") or row.get("ticker") or
                row.get("SYMBOL") or row.get("Stock") or
                row.get("stock") or ""
            ).strip().upper()
            
            if not ticker or len(ticker) > 10:
                continue
            
            # Shares
            shares_str = (
                row.get("Shares") or row.get("shares") or
                row.get("Quantity") or row.get("quantity") or
                row.get("QTY") or row.get("Qty") or "0"
            )
            try:
                shares = float(shares_str.replace(",", ""))
            except ValueError:
                shares = None
            
            # Value
            value_str = (
                row.get("Value") or row.get("value") or
                row.get("Market Value") or row.get("market_value") or
                row.get("Current Value") or row.get("Amount") or "0"
            )
            try:
                value = float(value_str.replace(",", "").replace("$", ""))
            except ValueError:
                value = None
            
            holdings.append({
                "ticker": ticker,
                "shares": shares,
                "value": value,
            })
        
        return holdings
        
    except Exception as e:
        print(f"CSV parse error: {e}")
        # Fallback: send to Claude
        return _extract_with_claude(content, "text/csv")


def _extract_with_claude(content: bytes, media_type: str) -> list[dict]:
    """Use Claude vision to extract holdings from an image or PDF."""
    b64 = base64.b64encode(content).decode("utf-8")
    
    if media_type == "text/csv":
        # For CSV that failed to parse, send as text
        text_content = content.decode("utf-8", errors="replace")
        messages = [{"role": "user", "content": [
            {"type": "text", "text": f"Extract portfolio holdings from this CSV data:\n\n{text_content[:5000]}"},
        ]}]
    elif "pdf" in media_type:
        messages = [{"role": "user", "content": [
            {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": b64}},
            {"type": "text", "text": "Extract all stock/ETF holdings from this brokerage statement."},
        ]}]
    else:
        messages = [{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
            {"type": "text", "text": "Extract all stock/ETF holdings from this brokerage screenshot."},
        ]}]
    
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system=EXTRACT_PROMPT,
            messages=messages,
        )
        
        raw = response.content[0].text.strip()
        
        # Clean markdown
        if "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()
            if raw.startswith("json"):
                raw = raw[4:].strip()
        
        # Extract JSON array
        import re
        json_match = re.search(r'\[.*\]', raw, re.DOTALL)
        if json_match:
            holdings = json.loads(json_match.group())
            if isinstance(holdings, list):
                return holdings
        
        return json.loads(raw) if raw.startswith("[") else []
        
    except Exception as e:
        print(f"Claude extraction error: {e}")
        return []


def _build_summary(holdings: list[dict]) -> str:
    """Build a natural language summary of the holdings."""
    if not holdings:
        return "No holdings could be extracted from the file."
    
    lines = []
    total_value = 0
    for h in holdings:
        ticker = h["ticker"]
        shares = h.get("shares")
        value = h.get("value")
        if shares and value:
            lines.append(f"{ticker}: {shares:.0f} shares (${value:,.0f})")
        elif shares:
            lines.append(f"{ticker}: {shares:.0f} shares")
        elif value:
            lines.append(f"{ticker}: ${value:,.0f}")
        else:
            lines.append(ticker)
        if value:
            total_value += value
    
    summary = f"Found {len(holdings)} positions"
    if total_value > 0:
        summary += f" totaling ${total_value:,.0f}"
    summary += ": " + ", ".join(lines[:10])
    if len(lines) > 10:
        summary += f" and {len(lines) - 10} more"
    
    return summary