import React, { useState, useEffect, useRef, useCallback } from 'react';
import VideoGrid from './components/VideoGrid';
import ChatPanel from './components/ChatPanel';
import MapPanel from './components/MapPanel';
import SettingsModal from './components/SettingsModal';
import StatusBar from './components/StatusBar';
import MetadataPanel from './components/MetadataPanel';

function App() {
  const [wsConnected, setWsConnected] = useState(false);
  const [frames, setFrames] = useState({});
  const [detections, setDetections] = useState([]);
  const [mapMarkers, setMapMarkers] = useState([]);
  const [crossTracks, setCrossTracks] = useState([]);
  const [systemStatus, setSystemStatus] = useState(null);
  const [showSettings, setShowSettings] = useState(false);
  const [selectedStream, setSelectedStream] = useState(null);
  const [mistralConnected, setMistralConnected] = useState(false);
  
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  const connectWebSocket = useCallback(() => {
    const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.hostname}:8000/ws`;
    
    try {
      wsRef.current = new WebSocket(wsUrl);
      
      wsRef.current.onopen = () => {
        console.log('WebSocket connected');
        setWsConnected(true);
      };
      
      wsRef.current.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.type === 'detection_update') {
          setFrames(data.frames || {});
          setDetections(data.detections || []);
          setMapMarkers(data.map_markers || []);
          setCrossTracks(data.cross_tracks || []);
        } else if (data.type === 'connected') {
          console.log('Connected with client ID:', data.client_id);
        }
      };
      
      wsRef.current.onclose = () => {
        console.log('WebSocket disconnected');
        setWsConnected(false);
        // Attempt reconnect after 3 seconds
        reconnectTimeoutRef.current = setTimeout(connectWebSocket, 3000);
      };
      
      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
      reconnectTimeoutRef.current = setTimeout(connectWebSocket, 3000);
    }
  }, []);

  useEffect(() => {
    connectWebSocket();
    fetchSystemStatus();
    
    // Fetch status periodically
    const statusInterval = setInterval(fetchSystemStatus, 5000);
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      clearInterval(statusInterval);
    };
  }, [connectWebSocket]);

  const fetchSystemStatus = async () => {
    try {
      const response = await fetch('/api/status');
      if (response.ok) {
        const status = await response.json();
        setSystemStatus(status);
        setMistralConnected(status.mistral_connected);
      }
    } catch (error) {
      console.error('Failed to fetch status:', error);
    }
  };

  const handleStreamSelect = (streamId) => {
    setSelectedStream(streamId === selectedStream ? null : streamId);
  };

  return (
    <div className="min-h-screen p-4 lg:p-6">
      {/* Header */}
      <header className="glass mb-6 p-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <img src="/drone.svg" alt="Drone" className="w-10 h-10" />
          <div>
            <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
              Drone Detection System
            </h1>
            <p className="text-sm text-gray-400">YOLO-powered cross-screen tracking</p>
          </div>
        </div>
        
        <div className="flex items-center gap-4">
          <StatusBar 
            wsConnected={wsConnected}
            mistralConnected={mistralConnected}
            systemStatus={systemStatus}
          />
          <button 
            onClick={() => setShowSettings(true)}
            className="btn btn-secondary flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            Settings
          </button>
        </div>
      </header>

      {/* Main Content */}
      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
        {/* Video Grid - Takes 3 columns on xl screens */}
        <div className="xl:col-span-3 space-y-6">
          <VideoGrid 
            frames={frames}
            detections={detections}
            crossTracks={crossTracks}
            selectedStream={selectedStream}
            onStreamSelect={handleStreamSelect}
          />
          
          {/* Map Panel */}
          <div className="glass p-4">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
              </svg>
              Live Tracking Map
            </h2>
            <MapPanel markers={mapMarkers} crossTracks={crossTracks} />
          </div>
        </div>

        {/* Right Sidebar - Chat and Metadata */}
        <div className="space-y-6">
          {/* Chat Panel */}
          <div className="glass p-4 h-[500px]">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
              AI Assistant
              {mistralConnected && <span className="status-dot online ml-2"></span>}
            </h2>
            <ChatPanel mistralConnected={mistralConnected} />
          </div>

          {/* Metadata Panel */}
          <div className="glass p-4">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Detection Metadata
            </h2>
            <MetadataPanel 
              detections={detections}
              crossTracks={crossTracks}
              selectedStream={selectedStream}
            />
          </div>
        </div>
      </div>

      {/* Settings Modal */}
      {showSettings && (
        <SettingsModal 
          onClose={() => setShowSettings(false)}
          onMistralUpdate={(connected) => setMistralConnected(connected)}
        />
      )}
    </div>
  );
}

export default App;
