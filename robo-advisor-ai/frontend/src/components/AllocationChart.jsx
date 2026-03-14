import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'

const COLORS = ['#3b82f6', '#10b981', '#8b5cf6', '#f59e0b', '#ef4444', '#06b6d4', '#ec4899', '#84cc16']

export default function AllocationChart({ allocations }) {
  if (!allocations || allocations.length === 0) return null

  const data = allocations
    .filter(a => a.weight > 0.001)
    .map(a => ({
      name: a.ticker,
      value: Math.round(a.weight * 1000) / 10,
      dollars: a.dollar_amount,
      shares: a.shares,
    }))

  const CustomTooltip = ({ active, payload }) => {
    if (!active || !payload?.length) return null
    const d = payload[0].payload
    return (
      <div className="bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-xs shadow-xl">
        <p className="font-semibold text-dark-50">{d.name}</p>
        <p className="text-dark-300">{d.value}% — ${d.dollars?.toLocaleString()}</p>
        <p className="text-dark-400">~{d.shares} shares</p>
      </div>
    )
  }

  return (
    <div className="flex items-center gap-4">
      <div className="w-40 h-40">
        <ResponsiveContainer>
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={35}
              outerRadius={65}
              dataKey="value"
              stroke="none"
            >
              {data.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div className="flex flex-col gap-1.5">
        {data.map((d, i) => (
          <div key={d.name} className="flex items-center gap-2 text-xs">
            <div
              className="w-2.5 h-2.5 rounded-sm flex-shrink-0"
              style={{ backgroundColor: COLORS[i % COLORS.length] }}
            />
            <span className="text-dark-300 w-12">{d.name}</span>
            <span className="text-dark-100 font-medium">{d.value}%</span>
          </div>
        ))}
      </div>
    </div>
  )
}
