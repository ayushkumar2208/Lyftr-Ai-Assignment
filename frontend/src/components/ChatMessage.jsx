function ChatMessage({ message }) {
  const isAssistant = message.role === 'assistant'

  return (
    <div
      className={`message-row ${
        isAssistant ? 'assistant-row' : 'user-row'
      }`}
    >
      <div
        className={`message-card ${
          isAssistant ? 'assistant-card' : 'user-card'
        }`}
        data-testid={
          isAssistant ? 'assistant-message' : undefined
        }
      >
        <div className="message-role">
          {isAssistant ? 'AI' : 'You'}
        </div>

        <div className="message-content">
          {message.content}
        </div>

        {isAssistant && message.metadata && (
          <div className="metadata">
            <span
              className={`source-badge ${
                message.metadata.resolution_source === 'LLM_CACHE'
                  ? 'cache'
                  : 'live'
              }`}
              data-testid="meta-source"
            >
              {message.metadata.resolution_source}
            </span>

            <div className="metadata-grid">
              <div>
                <span className="metadata-label">Model</span>
                <span data-testid="meta-model">
                  {message.metadata.model}
                </span>
              </div>

              <div>
                <span className="metadata-label">Latency</span>
                <span data-testid="meta-latency">
                  {message.metadata.latency_ms} ms
                </span>
              </div>

              <div>
                <span className="metadata-label">Input</span>
                <span data-testid="meta-input-tokens">
                  {message.metadata.input_tokens}
                </span>
              </div>

              <div>
                <span className="metadata-label">Output</span>
                <span data-testid="meta-output-tokens">
                  {message.metadata.output_tokens}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default ChatMessage