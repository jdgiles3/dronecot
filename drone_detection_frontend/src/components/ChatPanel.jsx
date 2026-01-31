import React, { useState, useRef, useEffect } from 'react';

function ChatPanel({ mistralConnected }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: 'Hello! I\'m your AI assistant for drone detection analysis. Ask me about detected objects, tracking patterns, or any surveillance data.',
      timestamp: new Date().toISOString()
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = {
      role: 'user',
      content: input.trim(),
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          message: userMessage.content,
          include_history: true
        })
      });

      if (response.ok) {
        const data = await response.json();
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: data.answer,
          confidence: data.confidence,
          timestamp: new Date().toISOString()
        }]);
      } else {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: 'Sorry, I encountered an error processing your request. Please check if the Mistral API key is configured in settings.',
          timestamp: new Date().toISOString()
        }]);
      }
    } catch (error) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Connection error. Please ensure the backend server is running.',
        timestamp: new Date().toISOString()
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const clearHistory = async () => {
    try {
      await fetch('/api/chat/history', { method: 'DELETE' });
      setMessages([{
        role: 'assistant',
        content: 'Chat history cleared. How can I help you?',
        timestamp: new Date().toISOString()
      }]);
    } catch (error) {
      console.error('Failed to clear history:', error);
    }
  };

  const suggestedQueries = [
    "What drones were detected recently?",
    "Show tracking patterns",
    "Any cross-screen movements?",
    "Detection statistics"
  ];

  return (
    <div className="chat-container h-full flex flex-col">
      {/* Messages */}
      <div className="chat-messages flex-1 overflow-y-auto">
        {messages.map((msg, idx) => (
          <div 
            key={idx}
            className={`message ${msg.role} fade-in`}
          >
            <p className="text-sm">{msg.content}</p>
            {msg.confidence && (
              <p className="text-xs text-gray-400 mt-1">
                Confidence: {(msg.confidence * 100).toFixed(0)}%
              </p>
            )}
            <p className="text-xs text-gray-500 mt-1">
              {new Date(msg.timestamp).toLocaleTimeString()}
            </p>
          </div>
        ))}
        
        {isLoading && (
          <div className="message assistant">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce"></div>
              <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
              <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Suggested queries */}
      {messages.length <= 2 && (
        <div className="px-2 py-2 border-t border-white/10">
          <p className="text-xs text-gray-400 mb-2">Suggested queries:</p>
          <div className="flex flex-wrap gap-1">
            {suggestedQueries.map((query, idx) => (
              <button
                key={idx}
                onClick={() => setInput(query)}
                className="text-xs px-2 py-1 bg-white/10 rounded hover:bg-white/20 transition-colors"
              >
                {query}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-2 border-t border-white/10">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={mistralConnected ? "Ask about detections..." : "Configure API key in settings..."}
            disabled={isLoading}
            className="flex-1 text-sm"
          />
          <button 
            type="submit"
            disabled={isLoading || !input.trim()}
            className="btn btn-primary px-4 disabled:opacity-50"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
        
        <div className="flex justify-between items-center mt-2">
          <span className="text-xs text-gray-500">
            {mistralConnected ? (
              <span className="text-green-400">Mistral AI connected</span>
            ) : (
              <span className="text-yellow-400">API key required</span>
            )}
          </span>
          <button
            type="button"
            onClick={clearHistory}
            className="text-xs text-gray-400 hover:text-white transition-colors"
          >
            Clear history
          </button>
        </div>
      </form>
    </div>
  );
}

export default ChatPanel;
