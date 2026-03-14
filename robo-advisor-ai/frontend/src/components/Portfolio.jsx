import { BarChart3, TrendingUp, Shield, Zap } from 'lucide-react'
import AllocationChart from './AllocationChart'
import AssetCard from './AssetCard'

export default function Portfolio({ research, strategy }) {
  const hasData = research || strategy

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

  return (
    <div className="h-full overflow-y-auto">
      <div className="px-6 py-4 space-y-6">
        {/* Header */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-accent-green/20 flex items-center justify-center">
            <BarChart3 size={18} className="text-accent-green" />
          </div>
          <h2 className="text-sm font-semibold text-dark-50">Portfolio Dashboard</h2>
        </div>

        {/* Strategy Stats */}
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
