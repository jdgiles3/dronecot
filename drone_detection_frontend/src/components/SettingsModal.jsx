import React, { useState, useEffect } from 'react';

function SettingsModal({ onClose, onMistralUpdate }) {
  const [apiKey, setApiKey] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    // Check current connection status
    fetchMistralStatus();
  }, []);

  const fetchMistralStatus = async () => {
    try {
      const response = await fetch('/api/settings/mistral');
      if (response.ok) {
        const data = await response.json();
        setIsConnected(data.connected);
      }
    } catch (error) {
      console.error('Failed to fetch Mistral status:', error);
    }
  };

  const handleSaveApiKey = async () => {
    if (!apiKey.trim()) {
      setMessage('Please enter an API key');
      return;
    }

    setIsTesting(true);
    setMessage('');

    try {
      const response = await fetch('/api/settings/mistral', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ api_key: apiKey })
      });

      if (response.ok) {
        const data = await response.json();
        setIsConnected(data.connected);
        onMistralUpdate(data.connected);
        
        if (data.connected) {
          setMessage('API key saved and connection verified!');
          setApiKey('');
        } else {
          setMessage('API key saved but connection failed. Please check the key.');
        }
      } else {
        setMessage('Failed to save API key');
      }
    } catch (error) {
      setMessage('Error saving API key: ' + error.message);
    } finally {
      setIsTesting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="glass w-full max-w-md mx-4 p-6 fade-in">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold">Settings</h2>
          <button 
            onClick={onClose}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Mistral AI Settings */}
        <div className="space-y-4">
          <div>
            <h3 className="text-lg font-medium mb-2 flex items-center gap-2">
              <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
              Mistral AI Configuration
            </h3>
            
            <div className="flex items-center gap-2 mb-4">
              <span className={`status-dot ${isConnected ? 'online' : 'offline'}`}></span>
              <span className="text-sm">
                {isConnected ? 'Connected' : 'Not connected'}
              </span>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-sm text-gray-400 mb-1">API Key</label>
                <input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="Enter your Mistral API key"
                  className="w-full"
                />
              </div>

              <button
                onClick={handleSaveApiKey}
                disabled={isTesting}
                className="btn btn-primary w-full flex items-center justify-center gap-2"
              >
                {isTesting ? (
                  <>
                    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Testing...
                  </>
                ) : (
                  'Save & Test Connection'
                )}
              </button>

              {message && (
                <p className={`text-sm ${message.includes('verified') ? 'text-green-400' : 'text-yellow-400'}`}>
                  {message}
                </p>
              )}

              <p className="text-xs text-gray-500">
                Get your API key from{' '}
                <a 
                  href="https://console.mistral.ai/" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="text-blue-400 hover:underline"
                >
                  console.mistral.ai
                </a>
              </p>
            </div>
          </div>

          <hr className="border-white/10" />

          {/* Video Stream Settings */}
          <div>
            <h3 className="text-lg font-medium mb-2 flex items-center gap-2">
              <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
              Video Streams
            </h3>
            
            <p className="text-sm text-gray-400 mb-3">
              Currently running 6 simulated drone camera feeds. Upload custom videos or connect RTSP streams via the API.
            </p>

            <div className="glass-dark p-3 rounded-lg">
              <p className="text-xs text-gray-500 mb-2">API Endpoints:</p>
              <code className="text-xs text-blue-400 block">POST /api/streams - Add stream</code>
              <code className="text-xs text-blue-400 block">POST /api/upload/video - Upload video</code>
            </div>
          </div>

          <hr className="border-white/10" />

          {/* About */}
          <div>
            <h3 className="text-lg font-medium mb-2">About</h3>
            <p className="text-sm text-gray-400">
              Drone Detection System v1.0.0
            </p>
            <p className="text-xs text-gray-500 mt-1">
              YOLO-powered object detection with cross-screen tracking and RAG-based AI assistant.
            </p>
          </div>
        </div>

        <div className="mt-6 flex justify-end">
          <button onClick={onClose} className="btn btn-secondary">
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

export default SettingsModal;
