import { useEffect, useState } from 'react'
import { useWebSocket } from './hooks/useWebSocket'
import Chat from './components/Chat'
import Portfolio from './components/Portfolio'
import { BarChart3, MessageSquare, X, Menu } from 'lucide-react'

export default function App() {
  const {
    connected,
    sessionId,
    messages,
    status,
    isLoading,
    research,
    strategy,
    connect,
    sendMessage,
  } = useWebSocket()

  const [showDashboard, setShowDashboard] = useState(false)
  const hasDashboardData = research || strategy

  // Connect on mount
  useEffect(() => {
    connect()
  }, [connect])

  // Auto-show dashboard when data arrives
  useEffect(() => {
    if (hasDashboardData) setShowDashboard(true)
  }, [hasDashboardData])

  return (
    <div className="h-screen flex flex-col bg-dark-900">
      {/* Top bar */}
      <header className="flex items-center justify-between px-6 py-3 border-b border-dark-700 bg-dark-800/50 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <span className="text-xl">📈</span>
          <h1 className="text-sm font-bold text-dark-50 tracking-tight">
            RoboAdvisor AI
          </h1>
          {sessionId && (
            <span className="text-[10px] text-dark-500 font-mono">
              {sessionId.slice(0, 8)}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* Dashboard toggle (mobile + always) */}
          {hasDashboardData && (
            <button
              onClick={() => setShowDashboard(!showDashboard)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                showDashboard
                  ? 'bg-accent-green/20 text-accent-green'
                  : 'bg-dark-700 text-dark-300 hover:text-dark-100'
              }`}
            >
              <BarChart3 size={14} />
              <span className="hidden sm:inline">Dashboard</span>
            </button>
          )}
        </div>
      </header>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Chat panel */}
        <div className={`flex-1 flex flex-col min-w-0 ${
          showDashboard ? 'hidden md:flex md:w-1/2 lg:w-2/5' : 'w-full'
        }`}>
          <Chat
            messages={messages}
            onSend={sendMessage}
            isLoading={isLoading}
            status={status}
            connected={connected}
          />
        </div>

        {/* Dashboard panel */}
        {showDashboard && (
          <div className="flex-1 flex flex-col min-w-0 border-l border-dark-700 bg-dark-800/30 md:w-1/2 lg:w-3/5">
            {/* Mobile close button */}
            <div className="md:hidden flex justify-end px-4 py-2">
              <button
                onClick={() => setShowDashboard(false)}
                className="p-1.5 rounded-lg bg-dark-700 text-dark-300"
              >
                <X size={16} />
              </button>
            </div>
            <Portfolio research={research} strategy={strategy} />
          </div>
        )}

        {/* Mobile chat button when dashboard is showing */}
        {showDashboard && (
          <button
            onClick={() => setShowDashboard(false)}
            className="md:hidden fixed bottom-6 left-6 w-12 h-12 rounded-full bg-accent-blue 
                     text-white shadow-lg flex items-center justify-center z-10"
          >
            <MessageSquare size={20} />
          </button>
        )}
      </div>
    </div>
  )
}
