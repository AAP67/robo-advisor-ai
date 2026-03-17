import { useState, useRef, useCallback, useEffect } from 'react'

const API_HOST = 'robo-advisor-ai-production.up.railway.app'
const WS_BASE = window.location.hostname === 'localhost'
  ? 'ws://localhost:8000'
  : 'wss://' + API_HOST

export function useWebSocket() {
  const [connected, setConnected] = useState(false)
  const [sessionId, setSessionId] = useState(null)
  const [messages, setMessages] = useState([])
  const [status, setStatus] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [research, setResearch] = useState(null)
  const [strategy, setStrategy] = useState(null)

  const wsRef = useRef(null)
  const reconnectTimeout = useRef(null)

  const connect = useCallback((existingSessionId = 'new') => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) return

    const ws = new WebSocket(WS_BASE + '/ws/' + existingSessionId)
    wsRef.current = ws

    ws.onopen = () => {
      setConnected(true)
      setStatus('')
    }

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)

      switch (data.type) {
        case 'session':
          setSessionId(data.session_id)
          break
        case 'status':
          setStatus(data.message)
          break
        case 'research':
          setResearch(data.data)
          // Signal to Francium parent
          try {
            const tickers = (data.data || []).map(r => r.ticker)
            const sectors = [...new Set((data.data || []).map(r => r.fundamentals?.sector).filter(Boolean))]
            window.parent.postMessage({
              type: 'francium_signal',
              toolId: 'robo-advisor',
              event: 'research_received',
              data: { tickers_researched: tickers, sectors }
            }, '*')
          } catch (e) { /* silent */ }
          break
        case 'strategy':
          setStrategy(data.data)
          // Signal to Francium parent
          try {
            const s = data.data
            window.parent.postMessage({
              type: 'francium_signal',
              toolId: 'robo-advisor',
              event: 'strategy_received',
              data: {
                expected_return: s.expected_annual_return,
                expected_volatility: s.expected_volatility,
                sharpe_ratio: s.sharpe_ratio,
                reasoning: (s.reasoning || '').slice(0, 500),
                top_allocations: (s.allocations || [])
                  .filter(a => a.weight > 0.01)
                  .sort((a, b) => b.weight - a.weight)
                  .slice(0, 10)
                  .map(a => ({ ticker: a.ticker, weight: a.weight }))
              }
            }, '*')
          } catch (e) { /* silent */ }
          break
        case 'response':
          setMessages(prev => [...prev, {
            role: 'assistant',
            content: data.content,
          }])
          setIsLoading(false)
          setStatus('')
          break
        case 'error':
          setMessages(prev => [...prev, {
            role: 'assistant',
            content: 'Error: ' + data.message,
          }])
          setIsLoading(false)
          setStatus('')
          break
        default:
          break
      }
    }

    ws.onclose = () => {
      setConnected(false)
      reconnectTimeout.current = setTimeout(() => {
        connect(existingSessionId)
      }, 3000)
    }

    ws.onerror = () => {
      setConnected(false)
    }
  }, [])

  const sendMessage = useCallback((text) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return

    setMessages(prev => [...prev, { role: 'user', content: text }])
    setIsLoading(true)
    setStatus('Processing...')

    wsRef.current.send(JSON.stringify({ message: text }))
  }, [])

  const disconnect = useCallback(() => {
    if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current)
    if (wsRef.current) wsRef.current.close()
  }, [])

  useEffect(() => {
    return () => disconnect()
  }, [disconnect])

  return {
    connected,
    sessionId,
    messages,
    status,
    isLoading,
    research,
    strategy,
    connect,
    sendMessage,
    disconnect,
  }
}