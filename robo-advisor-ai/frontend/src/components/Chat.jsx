import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, Loader2, Upload } from 'lucide-react'

const API_HOST = window.location.hostname === 'localhost'
  ? 'http://localhost:8000'
  : 'https://robo-advisor-ai-production.up.railway.app'

export default function Chat({ messages, onSend, isLoading, status, connected }) {
  const [input, setInput] = useState('')
  const [uploading, setUploading] = useState(false)
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)
  const fileInputRef = useRef(null)

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, status])

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return
    const query = input.trim()
    onSend(query)
    setInput('')
    // Signal to Francium parent
    try {
      window.parent.postMessage({
        type: 'francium_signal',
        toolId: 'robo-advisor',
        event: 'user_query',
        data: { query }
      }, '*')
    } catch (e) { /* silent */ }
  }

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    
    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      
      const res = await fetch(API_HOST + '/upload-portfolio', {
        method: 'POST',
        body: formData,
      })
      const data = await res.json()
      
      if (data.holdings && data.holdings.length > 0) {
        // Format holdings as a natural language message for the intake agent
        const holdingsText = data.holdings
          .map(h => {
            let parts = [h.ticker]
            if (h.shares) parts.push(`${h.shares} shares`)
            if (h.value) parts.push(`$${h.value.toLocaleString()}`)
            return parts.join(': ')
          })
          .join(', ')
        
        const message = `I have an existing portfolio: ${holdingsText}. Please build on top of these holdings.`
        setInput(message)
        inputRef.current?.focus()
      } else {
        setInput('Could not extract holdings from the file. Please describe your portfolio manually.')
        inputRef.current?.focus()
      }
    } catch (err) {
      console.error('Upload error:', err)
      setInput('File upload failed. Please describe your portfolio manually.')
      inputRef.current?.focus()
    }
    setUploading(false)
    // Reset file input
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const renderContent = (text) => {
    // Simple markdown-like rendering for bold
    return text.split('\n').map((line, i) => {
      const parts = line.split(/(\*\*.*?\*\*)/g).map((part, j) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return <strong key={j}>{part.slice(2, -2)}</strong>
        }
        return part
      })
      return (
        <span key={i}>
          {parts}
          {i < text.split('\n').length - 1 && <br />}
        </span>
      )
    })
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-3 px-6 py-4 border-b border-dark-700">
        <div className="w-8 h-8 rounded-lg bg-accent-blue/20 flex items-center justify-center">
          <Bot size={18} className="text-accent-blue" />
        </div>
        <div>
          <h2 className="text-sm font-semibold text-dark-50">RoboAdvisor AI</h2>
          <div className="flex items-center gap-1.5">
            <div className={`w-1.5 h-1.5 rounded-full ${connected ? 'bg-accent-green' : 'bg-dark-400'}`} />
            <span className="text-xs text-dark-400">
              {connected ? 'Connected' : 'Connecting...'}
            </span>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-16 h-16 rounded-2xl bg-accent-blue/10 flex items-center justify-center mb-4">
              <Bot size={32} className="text-accent-blue" />
            </div>
            <h3 className="text-lg font-semibold text-dark-100 mb-2">
              AI Portfolio Advisor
            </h3>
            <p className="text-sm text-dark-400 max-w-md">
              Tell me about your investment goals, risk tolerance, and preferences. 
              I'll build an optimized portfolio using Black-Litterman optimization.
            </p>
            <div className="flex flex-wrap gap-2 mt-6 justify-center">
              {[
                "I have $100K, moderate risk, 5yr horizon, interested in AI",
                "Help me invest $50K aggressively in tech and clean energy",
                "Conservative portfolio with $200K for retirement in 20 years",
              ].map((suggestion, i) => (
                <button
                  key={i}
                  onClick={() => { setInput(suggestion); inputRef.current?.focus() }}
                  className="text-xs px-3 py-2 rounded-lg bg-dark-700 text-dark-300 
                           hover:bg-dark-600 hover:text-dark-100 transition-colors text-left"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : ''}`}>
            {msg.role === 'assistant' && (
              <div className="w-7 h-7 rounded-lg bg-accent-blue/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                <Bot size={14} className="text-accent-blue" />
              </div>
            )}
            <div className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
              msg.role === 'user'
                ? 'bg-accent-blue text-white rounded-br-md'
                : 'bg-dark-700 text-dark-100 rounded-bl-md'
            }`}>
              <div className="message-content">
                {renderContent(msg.content)}
              </div>
            </div>
            {msg.role === 'user' && (
              <div className="w-7 h-7 rounded-lg bg-dark-600 flex items-center justify-center flex-shrink-0 mt-0.5">
                <User size={14} className="text-dark-300" />
              </div>
            )}
          </div>
        ))}

        {/* Loading / Status */}
        {isLoading && (
          <div className="flex gap-3">
            <div className="w-7 h-7 rounded-lg bg-accent-blue/20 flex items-center justify-center flex-shrink-0">
              <Bot size={14} className="text-accent-blue" />
            </div>
            <div className="bg-dark-700 rounded-2xl rounded-bl-md px-4 py-3">
              <div className="flex items-center gap-2 text-sm text-dark-300">
                <Loader2 size={14} className="animate-spin" />
                {status || 'Thinking...'}
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="px-6 py-4 border-t border-dark-700">
        <form onSubmit={handleSubmit} className="flex gap-2">
          {/* Hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.pdf,.png,.jpg,.jpeg,.webp"
            hidden
            onChange={handleFileUpload}
          />
          {/* Upload button */}
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isLoading || !connected || uploading}
            title="Upload portfolio (CSV, PDF, or screenshot)"
            className="bg-dark-700 hover:bg-dark-600 disabled:opacity-30
                     text-dark-300 hover:text-dark-100 rounded-xl px-3 py-3
                     transition-colors flex items-center"
          >
            {uploading
              ? <Loader2 size={16} className="animate-spin" />
              : <Upload size={16} />
            }
          </button>
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Describe your investment goals..."
            disabled={isLoading || !connected}
            className="flex-1 bg-dark-700 text-dark-100 rounded-xl px-4 py-3 text-sm
                     placeholder-dark-400 border border-dark-600 
                     focus:outline-none focus:border-accent-blue focus:ring-1 focus:ring-accent-blue/50
                     disabled:opacity-50 transition-colors"
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading || !connected}
            className="bg-accent-blue hover:bg-blue-600 disabled:bg-dark-600 
                     disabled:cursor-not-allowed text-white rounded-xl px-4 py-3 
                     transition-colors flex items-center gap-2"
          >
            <Send size={16} />
          </button>
        </form>
        <p className="text-[10px] text-dark-500 mt-2 text-center">
          Upload a brokerage CSV, PDF statement, or screenshot to import your existing portfolio
        </p>
      </div>
    </div>
  )
}