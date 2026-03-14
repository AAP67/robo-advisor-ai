import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

export default function AssetCard({ research }) {
  const { ticker, company_name, current_price, technicals, fundamentals, sentiment } = research

  const sentScore = sentiment?.score || 0
  const sentLabel = sentScore >= 0.3 ? 'Bullish' : sentScore <= -0.3 ? 'Bearish' : 'Neutral'
  const sentColor = sentScore >= 0.3 ? 'text-accent-green' : sentScore <= -0.3 ? 'text-accent-red' : 'text-accent-yellow'
  const SentIcon = sentScore >= 0.3 ? TrendingUp : sentScore <= -0.3 ? TrendingDown : Minus

  const rsi = technicals?.rsi_14
  const rsiLabel = rsi ? (rsi < 30 ? 'Oversold' : rsi > 70 ? 'Overbought' : 'Normal') : null
  const rsiColor = rsi ? (rsi < 30 ? 'text-accent-green' : rsi > 70 ? 'text-accent-red' : 'text-dark-300') : ''

  return (
    <div className="bg-dark-700 rounded-xl p-4 border border-dark-600 hover:border-dark-500 transition-colors">
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <h4 className="text-sm font-semibold text-dark-50">{ticker}</h4>
          <p className="text-xs text-dark-400 truncate max-w-[140px]">{company_name || ''}</p>
        </div>
        <span className="text-sm font-semibold text-dark-100">
          ${current_price?.toFixed(2)}
        </span>
      </div>

      {/* Metrics grid */}
      <div className="grid grid-cols-2 gap-2 text-xs">
        {/* Sentiment */}
        <div className="flex items-center gap-1.5">
          <SentIcon size={12} className={sentColor} />
          <span className={sentColor}>{sentLabel}</span>
          <span className="text-dark-500">({sentScore > 0 ? '+' : ''}{sentScore.toFixed(1)})</span>
        </div>

        {/* RSI */}
        {rsi && (
          <div className="flex items-center gap-1.5">
            <span className="text-dark-400">RSI</span>
            <span className={rsiColor}>{rsi.toFixed(0)}</span>
            {rsiLabel !== 'Normal' && (
              <span className={`text-[10px] ${rsiColor}`}>({rsiLabel})</span>
            )}
          </div>
        )}

        {/* P/E */}
        {fundamentals?.pe_ratio && (
          <div className="flex items-center gap-1.5">
            <span className="text-dark-400">P/E</span>
            <span className="text-dark-200">{fundamentals.pe_ratio.toFixed(1)}</span>
          </div>
        )}

        {/* Sector */}
        {fundamentals?.sector && (
          <div className="truncate">
            <span className="text-dark-400">{fundamentals.sector}</span>
          </div>
        )}
      </div>

      {/* Sentiment summary */}
      {sentiment?.summary && (
        <p className="text-[11px] text-dark-400 mt-2 leading-relaxed line-clamp-2">
          {sentiment.summary}
        </p>
      )}
    </div>
  )
}
