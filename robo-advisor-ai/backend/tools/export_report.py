"""
RoboAdvisor AI — Export Report
Generates a styled HTML investment memo from the current strategy.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
import json

router = APIRouter()


class ExportRequest(BaseModel):
    strategy: dict
    profile: dict
    research: list[dict] = []


@router.post("/export-report")
async def export_report(req: ExportRequest):
    """Generate a styled HTML investment memo."""
    html = generate_report(req.strategy, req.profile, req.research)
    return HTMLResponse(content=html)


def generate_report(strategy: dict, profile: dict, research: list[dict]) -> str:
    """Build the full HTML report."""
    from datetime import datetime
    now = datetime.now().strftime("%B %d, %Y")
    
    allocations = strategy.get("allocations", [])
    sorted_allocs = sorted(allocations, key=lambda a: a.get("weight", 0), reverse=True)
    risk_contribs = strategy.get("risk_contributions", {})
    benchmark = strategy.get("benchmark", {})
    bl_params = strategy.get("bl_params", {})
    
    # Build allocation rows
    alloc_rows = ""
    for a in sorted_allocs:
        if a.get("weight", 0) < 0.001:
            continue
        rc = risk_contribs.get(a["ticker"], 0)
        rc_color = "red" if rc > a.get("weight", 0) * 1.5 else "green" if rc < a.get("weight", 0) * 0.7 else "text"
        alloc_rows += f"""
        <tr>
            <td><strong>{a['ticker']}</strong></td>
            <td class="dim">{a.get('company_name', '') or ''}</td>
            <td class="right">{a['weight']:.1%}</td>
            <td class="right">${a.get('dollar_amount', 0):,.0f}</td>
            <td class="right">{a.get('shares', 0)}</td>
            <td class="right {rc_color}">{rc:.1%}</td>
        </tr>"""
    
    # Build research cards
    research_cards = ""
    for r in research:
        f = r.get("fundamentals", {})
        t = r.get("technicals", {})
        s = r.get("sentiment", {})
        
        sent_score = s.get("score", 0)
        sent_color = "green" if sent_score >= 0.3 else "red" if sent_score <= -0.3 else "amber"
        
        rsi = t.get("rsi_14")
        rsi_text = ""
        if rsi:
            if rsi < 30:
                rsi_text = " (oversold)"
            elif rsi > 70:
                rsi_text = " (overbought)"
        
        research_cards += f"""
        <div class="research-card">
            <div class="research-header">
                <strong>{r['ticker']}</strong>
                <span class="dim">{r.get('company_name', '')}</span>
                <span class="price">${r.get('current_price', 0):.2f}</span>
            </div>
            <div class="research-row">
                <span>P/E: {f.get('pe_ratio', 'N/A')}</span>
                <span>Margin: {f'{f["profit_margin"]:.1%}' if f.get("profit_margin") else 'N/A'}</span>
                <span>RSI: {f'{rsi:.0f}{rsi_text}' if rsi else 'N/A'}</span>
                <span class="{sent_color}">Sentiment: {sent_score:+.1f}</span>
            </div>
            {f'<div class="research-summary">{_esc(s.get("summary", ""))}</div>' if s.get("summary") else ''}
        </div>"""
    
    # Benchmark comparison
    bench_html = ""
    if benchmark:
        ret_diff = strategy.get('expected_annual_return', 0) - benchmark.get('expected_return', 0)
        vol_diff = strategy.get('expected_volatility', 0) - benchmark.get('volatility', 0)
        sharpe_diff = strategy.get('sharpe_ratio', 0) - benchmark.get('sharpe_ratio', 0)
        bench_html = f"""
    <div class="card">
        <h2>Portfolio vs S&P 500</h2>
        <table>
            <tr><th></th><th class="right">Your Portfolio</th><th class="right">S&P 500</th><th class="right">Difference</th></tr>
            <tr>
                <td>Expected Return</td>
                <td class="right">{strategy.get('expected_annual_return', 0):.1%}</td>
                <td class="right">{benchmark.get('expected_return', 0):.1%}</td>
                <td class="right {'green' if ret_diff >= 0 else 'red'}">{'+'if ret_diff>=0 else ''}{ret_diff:.1%}</td>
            </tr>
            <tr>
                <td>Volatility</td>
                <td class="right">{strategy.get('expected_volatility', 0):.1%}</td>
                <td class="right">{benchmark.get('volatility', 0):.1%}</td>
                <td class="right {'red' if vol_diff > 0 else 'green'}">{'+'if vol_diff>=0 else ''}{vol_diff:.1%}</td>
            </tr>
            <tr>
                <td>Sharpe Ratio</td>
                <td class="right">{strategy.get('sharpe_ratio', 0):.2f}</td>
                <td class="right">{benchmark.get('sharpe_ratio', 0):.2f}</td>
                <td class="right {'green' if sharpe_diff >= 0 else 'red'}">{'+'if sharpe_diff>=0 else ''}{sharpe_diff:.2f}</td>
            </tr>
        </table>
    </div>"""

    # View confidences
    confidences = bl_params.get("view_confidences", {})
    conf_rows = ""
    for ticker, conf in sorted(confidences.items(), key=lambda x: x[1], reverse=True):
        conf_rows += f"<tr><td>{ticker}</td><td class='right'>{conf:.0%}</td></tr>"

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>RoboAdvisor AI — Investment Memo | {now}</title>
<style>{CSS}</style>
</head>
<body>
<div class="container">

<div class="header">
    <h1>📈 RoboAdvisor <span class="accent">AI</span> — Investment Memo</h1>
    <p class="date">Generated {now}</p>
</div>

<!-- Investor Profile -->
<div class="card">
    <h2>Investor Profile</h2>
    <div class="stats-row">
        <div class="stat">
            <div class="stat-num">${profile.get('capital', 0):,.0f}</div>
            <div class="stat-label">Capital</div>
        </div>
        <div class="stat">
            <div class="stat-num">{profile.get('risk_tolerance', 5)}/10</div>
            <div class="stat-label">Risk ({profile.get('risk_category', 'moderate')})</div>
        </div>
        <div class="stat">
            <div class="stat-num">{profile.get('horizon_years', 5)}yr</div>
            <div class="stat-label">Horizon</div>
        </div>
    </div>
    {f"<p class='dim' style='margin-top:12px'>Sectors: {', '.join(profile.get('sector_preferences', []))}</p>" if profile.get('sector_preferences') else ''}
    {f"<p class='dim'>Constraints: {', '.join(profile.get('constraints', []))}</p>" if profile.get('constraints') else ''}
</div>

<!-- Portfolio Stats -->
<div class="card">
    <h2>Portfolio Summary</h2>
    <div class="stats-row">
        <div class="stat">
            <div class="stat-num green">{strategy.get('expected_annual_return', 0):.1%}</div>
            <div class="stat-label">Expected Return</div>
        </div>
        <div class="stat">
            <div class="stat-num amber">{strategy.get('expected_volatility', 0):.1%}</div>
            <div class="stat-label">Volatility</div>
        </div>
        <div class="stat">
            <div class="stat-num blue">{strategy.get('sharpe_ratio', 0):.2f}</div>
            <div class="stat-label">Sharpe Ratio</div>
        </div>
    </div>
</div>

{bench_html}

<!-- Allocations -->
<div class="card">
    <h2>Portfolio Allocation</h2>
    <table>
        <tr><th>Ticker</th><th>Company</th><th class="right">Weight</th><th class="right">Value</th><th class="right">Shares</th><th class="right">Risk %</th></tr>
        {alloc_rows}
    </table>
</div>

<!-- Strategy -->
<div class="card">
    <h2>Strategy Reasoning</h2>
    <p>{_esc(strategy.get('reasoning', 'N/A'))}</p>
</div>

<!-- Research -->
{f'''<div class="card">
    <h2>Research ({len(research)} Assets)</h2>
    {research_cards}
</div>''' if research else ''}

<!-- BL Parameters -->
<div class="card">
    <h2>Black-Litterman Parameters</h2>
    <div class="stats-row">
        <div class="stat">
            <div class="stat-num">{bl_params.get('tau', 0.05)}</div>
            <div class="stat-label">Tau (uncertainty)</div>
        </div>
        <div class="stat">
            <div class="stat-num">{bl_params.get('risk_aversion', 2.5):.1f}</div>
            <div class="stat-label">Risk Aversion</div>
        </div>
    </div>
    {f'''<h3 style="margin-top:16px; font-size:12px; color:#888;">View Confidences</h3>
    <table><tr><th>Ticker</th><th class="right">Confidence</th></tr>{conf_rows}</table>''' if conf_rows else ''}
</div>

<div class="footer">
    <p>RoboAdvisor AI — Investment Memo · Built by Karan Rajpal</p>
    <p class="dim">Print this page (Ctrl/Cmd + P) to save as PDF</p>
</div>

</div>
</body>
</html>"""


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; background: #0a0e17; color: #c8cdd5; line-height: 1.6; }
.container { max-width: 820px; margin: 0 auto; padding: 40px 24px; }
.header { margin-bottom: 32px; border-bottom: 1px solid #1e2538; padding-bottom: 20px; }
h1 { font-size: 26px; color: #e8ecf0; font-weight: 700; }
h2 { font-size: 14px; color: #4ade80; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 14px; font-weight: 600; }
h3 { font-size: 12px; color: #888; }
.accent { color: #4ade80; }
.date { font-size: 13px; color: #555; font-family: monospace; margin-top: 4px; }
.dim { font-size: 13px; color: #666; }
.card { background: #111827; border: 1px solid #1e2538; border-radius: 12px; padding: 24px; margin-bottom: 16px; }
.stats-row { display: flex; gap: 32px; flex-wrap: wrap; }
.stat { text-align: center; }
.stat-num { font-size: 26px; font-weight: 700; color: #e8ecf0; font-family: monospace; }
.stat-label { font-size: 11px; color: #666; text-transform: uppercase; letter-spacing: 1px; margin-top: 2px; }
.green { color: #4ade80; }
.amber { color: #fbbf24; }
.red { color: #f87171; }
.blue { color: #60a5fa; }
.text { color: #c8cdd5; }
table { width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 8px; }
th { text-align: left; padding: 8px 10px; border-bottom: 1px solid #1e2538; color: #888; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; font-weight: 500; }
td { padding: 8px 10px; border-bottom: 1px solid #141b2a; }
.right { text-align: right; }
.research-card { background: #0d1320; border: 1px solid #1e2538; border-radius: 8px; padding: 14px; margin-bottom: 10px; }
.research-header { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }
.research-header strong { color: #e8ecf0; font-size: 14px; }
.price { margin-left: auto; color: #e8ecf0; font-family: monospace; }
.research-row { display: flex; gap: 16px; font-size: 12px; color: #888; flex-wrap: wrap; }
.research-summary { font-size: 12px; color: #777; margin-top: 6px; font-style: italic; }
.footer { text-align: center; margin-top: 32px; padding-top: 20px; border-top: 1px solid #1e2538; }
.footer p { font-size: 12px; color: #555; }
@media print {
    body { background: white; color: #222; }
    .card { border-color: #ddd; background: #fafafa; }
    h2, .accent { color: #16a34a; }
    .research-card { background: #f5f5f5; border-color: #ddd; }
    td, th { border-color: #ddd; }
    .footer .dim { display: none; }
}
"""