import { useState } from "react";
import "./App.css";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function App() {
  const [sessionId] = useState(() => crypto.randomUUID());
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function sendMessage(e) {
    e.preventDefault();
    if (!message.trim() || loading) return;

    const text = message.trim();
    setMessage("");
    setMessages((old) => [...old, { role: "user", content: text }]);
    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, message: text }),
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Request failed");

      setMessages((old) => [
        ...old,
        { role: "assistant", content: data.reply, metadata: data.metadata },
      ]);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="app">
      <header className="header">
        <h1>? Lyftr AI</h1>
        <span>? AI Assistant</span>
      </header>

      <section className="chat-container">
        <div className="chat-heading">
          <h2>Your Intelligent Assistant</h2>
          <p>Smart AI responses with caching and automatic key failover.</p>
        </div>

        <div className="messages">
          {messages.length === 0 && (
            <div className="welcome">
              <h2>How can I help you today?</h2>
              <p>Start a conversation with Lyftr AI.</p>
            </div>
          )}

          {messages.map((item, index) => (
            <article
              key={index}
              className={`message ${item.role}`}
              data-testid={item.role === "assistant" ? "assistant-message" : undefined}
            >
              <strong>{item.role === "user" ? "You" : "Lyftr AI"}</strong>
              <p>{item.content}</p>
              {item.metadata && (
                <div className="metadata">
                  <span data-testid="meta-source">Source: {item.metadata.resolution_source}</span>
                  <span data-testid="meta-model">Model: {item.metadata.model}</span>
                  <span data-testid="meta-latency">Latency: {item.metadata.latency_ms} ms</span>
                  <span data-testid="meta-input-tokens">Input: {item.metadata.input_tokens}</span>
                  <span data-testid="meta-output-tokens">Output: {item.metadata.output_tokens}</span>
                  <span>Key: {item.metadata.key_id}</span>
                  <span>Fallbacks: {item.metadata.fallback_attempts}</span>
                </div>
              )}
            </article>
          ))}
          {loading && <p className="loading">Lyftr AI is thinking...</p>}
        </div>

        {error && <p className="error">{error}</p>}

        <form className="chat-form" onSubmit={sendMessage}>
          <input
            data-testid="chat-input"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Type your message..."
            disabled={loading}
          />
          <button data-testid="send-button" disabled={loading || !message.trim()}>
            Send
          </button>
        </form>
        <p className="session">Session: {sessionId}</p>
      </section>
    </main>
  );
}
