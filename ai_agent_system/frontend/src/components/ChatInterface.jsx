import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

function ChatInterface({ messages, onSendMessage, agents }) {
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

    setIsLoading(true);
    await onSendMessage(input.trim());
    setInput('');
    setIsLoading(false);
  };

  const suggestedQueries = [
    "Analyze recent patterns",
    "Show system alerts",
    "Generate daily report",
    "Search documents"
  ];

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-3 pr-2">
        <AnimatePresence>
          {messages.length === 0 ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-center py-8"
            >
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-neon-blue/20 to-neon-purple/20 flex items-center justify-center">
                <svg className="w-8 h-8 text-neon-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
              </div>
              <p className="text-gray-400 text-sm mb-4">
                Multi-agent AI system ready
              </p>
              <div className="flex flex-wrap gap-2 justify-center">
                {suggestedQueries.map((query, i) => (
                  <button
                    key={i}
                    onClick={() => setInput(query)}
                    className="text-xs px-3 py-1.5 rounded-full bg-white/5 border border-white/10 hover:border-neon-blue/50 hover:bg-neon-blue/10 transition-all"
                  >
                    {query}
                  </button>
                ))}
              </div>
            </motion.div>
          ) : (
            messages.map((msg, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className={`chat-message ${msg.role}`}
              >
                {msg.role === 'assistant' && msg.agent && (
                  <div className="text-xs text-neon-purple mb-1 font-orbitron">
                    {msg.agent.toUpperCase()} AGENT
                  </div>
                )}
                <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                <div className="text-xs text-gray-500 mt-1">
                  {new Date(msg.timestamp).toLocaleTimeString()}
                </div>
              </motion.div>
            ))
          )}
        </AnimatePresence>
        
        {isLoading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="chat-message assistant"
          >
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-neon-blue rounded-full animate-bounce" />
              <div className="w-2 h-2 bg-neon-purple rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
              <div className="w-2 h-2 bg-neon-pink rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
            </div>
          </motion.div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="mt-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask the AI agents..."
            disabled={isLoading}
            className="neon-input flex-1"
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="neon-button px-4 disabled:opacity-50"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
        
        <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
          <span>
            {agents.length} agents available
          </span>
          <span>
            {messages.length} messages
          </span>
        </div>
      </form>
    </div>
  );
}

export default ChatInterface;
