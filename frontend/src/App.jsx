import { useEffect, useRef, useState } from 'react'
import ChatMessage from './components/ChatMessage'
import './App.css'


function createSessionId() {
  if (window.crypto?.randomUUID) {
    return `s-${window.crypto.randomUUID()}`
  }

  return `s-${Date.now()}-${Math.random()
    .toString(36)
    .slice(2)}`
}


function App() {
  const [sessionId] = useState(createSessionId)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [systemPrompt, setSystemPrompt] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const messagesEndRef = useRef(null)

  const apiUrl =
    import.meta.env.VITE_API_URL ||
    'http://127.0.0.1:8000'


  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: 'smooth',
    })
  }, [messages, loading, error])


  const handleSubmit = async (event) => {
    event.preventDefault()

    const trimmedMessage = input.trim()

    if (!trimmedMessage || loading) {
      return
    }

    const userMessage = {
      role: 'user',
      content: trimmedMessage,
    }

    setMessages((current) => [
      ...current,
      userMessage,
    ])

    setInput('')
    setError('')
    setLoading(true)

    try {
      const requestBody = {
        session_id: sessionId,
        message: trimmedMessage,
      }

      if (systemPrompt.trim()) {
        requestBody.system_prompt =
          systemPrompt.trim()
      }

      const response = await fetch(
        `${apiUrl}/chat`,
        {
          method: 'POST',

          headers: {
            'Content-Type': 'application/json',
          },

          body: JSON.stringify(requestBody),
        },
      )

      let data

      try {
        data = await response.json()
      } catch {
        throw new Error(
          'Backend returned an invalid response.',
        )
      }

      if (!response.ok) {
        let detail = data.detail

        if (Array.isArray(detail)) {
          detail = detail
            .map((item) => item.msg)
            .join(', ')
        }

        throw new Error(
          detail ||
            `Request failed with status ${response.status}.`,
        )
      }

      const assistantMessage = {
        role: 'assistant',
        content: data.reply,
        metadata: data.metadata,
      }

      setMessages((current) => [
        ...current,
        assistantMessage,
      ])
    } catch (err) {
      const errorMessage =
        err instanceof Error
          ? err.message
          : 'Something went wrong.'

      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }


  const handleKeyDown = (event) => {
    if (
      event.key === 'Enter' &&
      !event.shiftKey
    ) {
      event.preventDefault()
      event.currentTarget.form?.requestSubmit()
    }
  }


  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <div className="brand-icon">
            L
          </div>

          <div>
            <h1>Lyftr AI</h1>
            <p>Resilient LLM Chat</p>
          </div>
        </div>

        <div className="status">
          <span className="status-dot" />
          Backend
        </div>
      </header>


      <main className="chat-layout">
        <section className="chat-panel">

          <div className="session-bar">
            <div>
              <span className="session-label">
                SESSION
              </span>

              <span className="session-id">
                {sessionId}
              </span>
            </div>

            <span className="session-state">
              Active
            </span>
          </div>


          <div className="messages">

            {messages.length === 0 &&
              !loading && (
                <div className="empty-state">
                  <div className="empty-icon">
                    ✦
                  </div>

                  <h2>
                    Start a conversation
                  </h2>

                  <p>
                    Send a message to begin
                    chatting with the AI.
                  </p>
                </div>
              )}


            {messages.map(
              (message, index) => (
                <ChatMessage
                  key={`${message.role}-${index}`}
                  message={message}
                />
              ),
            )}


            {loading && (
              <div className="message-row assistant-row">
                <div className="message-card assistant-card">

                  <div className="message-role">
                    AI
                  </div>

                  <div className="typing">
                    <span />
                    <span />
                    <span />
                  </div>

                </div>
              </div>
            )}


            {error && (
              <div
                className="error-message"
                role="alert"
              >
                <strong>
                  Unable to respond
                </strong>

                <span>
                  {error}
                </span>
              </div>
            )}


            <div ref={messagesEndRef} />

          </div>


          <form
            className="composer"
            onSubmit={handleSubmit}
          >

            <textarea
              data-testid="chat-input"
              value={input}
              onChange={(event) =>
                setInput(event.target.value)
              }
              onKeyDown={handleKeyDown}
              placeholder="Message Lyftr AI..."
              maxLength={4000}
              rows={1}
              disabled={loading}
            />

            <button
              data-testid="send-button"
              type="submit"
              disabled={
                loading || !input.trim()
              }
              aria-label="Send message"
            >
              {loading ? '…' : '↑'}
            </button>

          </form>
        </section>


        <aside className="settings-panel">

          <div className="settings-card">

            <h3>
              Session settings
            </h3>

            <label htmlFor="system-prompt">
              System prompt
            </label>

            <textarea
              id="system-prompt"
              data-testid="system-prompt-input"
              value={systemPrompt}
              onChange={(event) =>
                setSystemPrompt(
                  event.target.value,
                )
              }
              placeholder="Optional instructions for the AI..."
              rows={6}
              disabled={loading}
            />

            <p className="helper-text">
              Optional instructions applied
              to this chat session.
            </p>

          </div>


          <div className="info-card">

            <h3>
              Response metadata
            </h3>

            <p>
              Each AI response displays its
              resolution source, model,
              latency and per-request token
              usage.
            </p>

          </div>

        </aside>
      </main>
    </div>
  )
}


export default App