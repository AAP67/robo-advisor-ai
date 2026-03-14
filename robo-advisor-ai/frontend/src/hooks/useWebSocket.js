import { useState, useRef, useCallback, useEffect } from 'react'

const WS_BASE = window.location.hostname === 'localhost'
  ? 'ws://localhost:8000'
  : `wss://${window.location.hostname.replace('-5173', '-8000')}`
  
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
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const ws = new WebSocket(`${WS_BASE}/ws/${existingSessionId}`)
    wsRef.current = ws

    ws.onopen = () => {
      setConnected(true)
      setStatus('')
      console.log('WebSocket connected')
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
          break

        case 'strategy':
          setStrategy(data.data)
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
            content: `Error: ${data.message}`,
          }])
          setIsLoading(false)
          setStatus('')
          break

        default:
          console.log('Unknown message type:', data)
      }
    }

    ws.onclose = () => {
      setConnected(false)
      console.log('WebSocket disconnected')
      // Auto-reconnect after 3 seconds
      reconnectTimeout.current = setTimeout(() => {
        if (sessionId) connect(sessionId)
      }, 3000)
    }

    ws.onerror = (err) => {
      console.error('WebSocket error:', err)
      setConnected(false)
    }
  }, [sessionId])

  const sendMessage = useCallback((text) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.error('WebSocket not connected')
      return
    }

    // Add user message to local state
    setMessages(prev => [...prev, { role: 'user', content: text }])
    setIsLoading(true)
    setStatus('Processing...')

    // Send to server
    wsRef.current.send(JSON.stringify({ message: text }))
  }, [])

  const disconnect = useCallback(() => {
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current)
    }
    if (wsRef.current) {
      wsRef.current.close()
    }
  }, [])

  // Cleanup on unmount
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
