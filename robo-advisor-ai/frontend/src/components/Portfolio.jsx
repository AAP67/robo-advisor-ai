import { useState } from 'react'
import { BarChart3, TrendingUp, Shield, Zap, AlertTriangle, Target, Download } from 'lucide-react'
import AllocationChart from './AllocationChart'
import AssetCard from './AssetCard'

const API_HOST = window.location.hostname === 'localhost'
  ? 'http://localhost:8000'
  : 'https://robo-advisor-ai-production.up.railway.app'

export default function Portfolio({ research, strategy }) {
  const hasData = research || strategy
  const [exporting, setExporting] = useState(false)

  const handleExport = async () => {
    if (!strategy) return
    setExporting(true)
    try {
      const res = await fetch(API_HOST + '/export-report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          strategy,
          profile: strategy._profile || {},
          research: research || [],
        }),
      })
      const html = await res.text()
      const blob = new Blob([html], { type: 'text/html' })
      const url = URL.createObjectURL(blob)
      window.open(url, '_blank')
    } catch (e) {
      console.error('Export error:', e)
    }
    setExporting(false)
  }

  if (!hasData) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center px-8">
        <div className="w-16 h-16 rounded-2xl bg-dark-700 flex items-center justify-center mb-4">
          <BarChart3 size={32} className="text-dark-500" />
        </div>
        <h3 className="text-lg font-semibold text-dark-300 mb-2">Portfolio Dashboard</h3>
        <p className="text-sm text-dark-500">
          Start a conversation to see your portfolio take shape here.
        </p>
      </div>
    )
  }

  const benchmark = strategy?.benchmark
  const riskContribs = strategy?.risk_contributions || {}

  return (
    <div className="h-full overflow-y-auto">
      <div className="px-6 py-4 space-y-4">
        {/* Header + Export */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-accent-green/20 flex items-center justify-center">
              <BarChart3 size={18} className="text-accent-green" />
            </div>
            <h2 className="text-sm font-semibold text-dark-50">Portfolio Dashboard</h2>
          </div>
          {strategy && (
            <button
              onClick={handleExport}
              disabled={exporting}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium
                       bg-dark-700 text-dark-300 hover:text-dark-100 hover:bg-dark-600 transition-colors"
            >
              <Download size={12} />
              {exporting ? 'Exporting...' : 'Export Memo'}
            </button>
          )}
        </div>

        {strategy && (
          <div className="space-y-4">
            {/* Allocation Chart */}
            <div className="bg-dark-800 rounded-xl p-5 border border-dark-700">
              <h3 className="text-xs font-medium text-dark-400 uppercase tracking-wide mb-4">
                Allocation
              </h3>
              <AllocationChart allocations={strategy.allocations} />
            </div>

            {/* Stats Cards */}
            <div className="grid grid-cols-3 gap-3">
              <StatCard
                icon={<TrendingUp size={16} />}
                label="Expected Return"
                value={`${(strategy.expected_annual_return * 100).toFixed(1)}%`}
                color="text-accent-green"
                bgColor="bg-accent-green/10"
              />
              <StatCard
                icon={<Shield size={16} />}
                label="Volatility"
                value={`${(strategy.expected_volatility * 100).toFixed(1)}%`}
                color="text-accent-yellow"
                bgColor="bg-accent-yellow/10"
              />
              <StatCard
                icon={<Zap size={16} />}
                label="Sharpe Ratio"
                value={strategy.sharpe_ratio.toFixed(2)}
                color="text-accent-blue"
                bgColor="bg-accent-blue/10"
              />
            </div>

            {/* Benchmark Comparison */}
            {benchmark && (
              <div className="bg-dark-800 rounded-xl p-5 border border-dark-700">
                <h3 className="text-xs font-medium text-dark-400 uppercase tracking-wide mb-3">
                  <Target size={12} className="inline mr-1.5 -mt-0.5" />
                  vs S&P 500
                </h3>
                <div className="grid grid-cols-3 gap-4 text-center">
                  <CompareCell
                    label="Return"
                    yours={strategy.expected_annual_return}
                    bench={benchmark.expected_return}
                    format="pct"
                    higherBetter={true}
                  />
                  <CompareCell
                    label="Volatility"
                    yours={strategy.expected_volatility}
                    bench={benchmark.volatility}
                    format="pct"
                    higherBetter={false}
                  />
                  <CompareCell
                    label="Sharpe"
                    yours={strategy.sharpe_ratio}
                    bench={benchmark.sharpe_ratio}
                    format="dec"
                    higherBetter={true}
                  />
                </div>
              </div>
            )}

            {/* Risk Decomposition */}
            {Object.keys(riskContribs).length > 0 && (
              <div className="bg-dark-800 rounded-xl p-5 border border-dark-700">
                <h3 className="text-xs font-medium text-dark-400 uppercase tracking-wide mb-3">
                  <AlertTriangle size={12} className="inline mr-1.5 -mt-0.5" />
                  Risk Decomposition
                </h3>
                <div className="space-y-2">
                  {Object.entries(riskContribs)
                    .filter(([, rc]) => rc > 0.01)
                    .sort(([, a], [, b]) => b - a)
                    .map(([ticker, rc]) => {
                      const weight = strategy.allocations.find(a => a.ticker === ticker)?.weight || 0
                      const isConcentrated = rc > weight * 1.3
                      return (
                        <div key={ticker} className="flex items-center gap-3">
                          <span className="text-xs font-medium text-dark-200 w-12">{ticker}</span>
                          <div className="flex-1 h-2 bg-dark-700 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full ${isConcentrated ? 'bg-red-500/70' : 'bg-accent-green/50'}`}
                              style={{ width: `${Math.min(rc * 100, 100)}%` }}
                            />
                          </div>
                          <span className={`text-xs font-mono w-12 text-right ${isConcentrated ? 'text-red-400' : 'text-dark-300'}`}>
                            {(rc * 100).toFixed(1)}%
                          </span>
                        </div>
                      )
                    })}
                </div>
                <p className="text-[10px] text-dark-500 mt-3">
                  Red bars indicate positions contributing disproportionate risk relative to their weight.
                </p>
              </div>
            )}

            {/* Reasoning */}
            {strategy.reasoning && (
              <div className="bg-dark-800 rounded-xl p-5 border border-dark-700">
                <h3 className="text-xs font-medium text-dark-400 uppercase tracking-wide mb-2">
                  Strategy
                </h3>
                <p className="text-sm text-dark-200 leading-relaxed">
                  {strategy.reasoning}
                </p>
              </div>
            )}

            {/* Positions Table */}
            <div className="bg-dark-800 rounded-xl p-5 border border-dark-700">
              <h3 className="text-xs font-medium text-dark-400 uppercase tracking-wide mb-3">
                Positions
              </h3>
              <div className="space-y-2">
                {strategy.allocations
                  .filter(a => a.weight > 0.001)
                  .sort((a, b) => b.weight - a.weight)
                  .map(a => (
                    <div key={a.ticker} className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-dark-100 w-14">{a.ticker}</span>
                        <span className="text-dark-400 text-xs truncate max-w-[100px]">
                          {a.company_name || ''}
                        </span>
                      </div>
                      <div className="flex items-center gap-4 text-xs">
                        <span className="text-dark-300">{a.shares} shares</span>
                        <span className="text-dark-200 w-16 text-right">
                          ${a.dollar_amount?.toLocaleString()}
                        </span>
                        <span className="text-dark-100 font-medium w-12 text-right">
                          {(a.weight * 100).toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          </div>
        )}

        {/* Research Cards */}
        {research && research.length > 0 && (
          <div>
            <h3 className="text-xs font-medium text-dark-400 uppercase tracking-wide mb-3">
              Research ({research.length} assets)
            </h3>
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
              {research.map(r => (
                <AssetCard key={r.ticker} research={r} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}


function StatCard({ icon, label, value, color, bgColor }) {
  return (
    <div className="bg-dark-800 rounded-xl p-4 border border-dark-700">
      <div className={`w-8 h-8 rounded-lg ${bgColor} flex items-center justify-center mb-2`}>
        <span className={color}>{icon}</span>
      </div>
      <p className="text-[11px] text-dark-400 mb-0.5">{label}</p>
      <p className={`text-lg font-bold ${color}`}>{value}</p>
    </div>
  )
}


function CompareCell({ label, yours, bench, format, higherBetter }) {
  const diff = yours - bench
  const isGood = higherBetter ? diff >= 0 : diff <= 0
  
  const fmt = (v) => format === 'pct' ? `${(v * 100).toFixed(1)}%` : v.toFixed(2)
  const fmtDiff = (v) => {
    const prefix = v >= 0 ? '+' : ''
    return format === 'pct' ? `${prefix}${(v * 100).toFixed(1)}%` : `${prefix}${v.toFixed(2)}`
  }

  return (
    <div>
      <p className="text-[10px] text-dark-500 uppercase tracking-wide mb-1">{label}</p>
      <p className="text-sm font-bold text-dark-100">{fmt(yours)}</p>
      <p className="text-[10px] text-dark-500">vs {fmt(bench)}</p>
      <p className={`text-xs font-medium mt-0.5 ${isGood ? 'text-accent-green' : 'text-red-400'}`}>
        {fmtDiff(diff)}
      </p>
    </div>
  )
}