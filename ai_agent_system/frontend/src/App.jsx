import React, { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import GlassPanel from './components/GlassPanel';
import ChatInterface from './components/ChatInterface';
import StatsDisplay from './components/StatsDisplay';
import LiveMap from './components/LiveMap';
import AgentStatus from './components/AgentStatus';
import DataFlow from './components/DataFlow';

function App() {
  const [wsConnected, setWsConnected] = useState(false);
  const [stats, setStats] = useState({});
  const [agents, setAgents] = useState([]);
  const [events, setEvents] = useState([]);
  const [mapNodes, setMapNodes] = useState([]);
  const [chatMessages, setChatMessages] = useState([]);
  
  const wsRef = useRef(null);

  // Generate stars for background
  const stars = Array.from({ length: 100 }, (_, i) => ({
    id: i,
    left: `${Math.random() * 100}%`,
    top: `${Math.random() * 100}%`,
    delay: `${Math.random() * 3}s`,
    size: Math.random() * 2 + 1
  }));

  const connectWebSocket = useCallback(() => {
    const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.hostname}:8001/ws`;
    
    try {
      wsRef.current = new WebSocket(wsUrl);
      
      wsRef.current.onopen = () => {
        setWsConnected(true);
        console.log('WebSocket connected');
      };
      
      wsRef.current.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.type === 'connected') {
          setAgents(data.agents || []);
        } else if (data.type === 'stats_update') {
          setStats(data.stats || {});
          
          // Generate map nodes from stats
          if (data.orchestrator_stats) {
            generateMapNodes(data);
          }
        } else if (data.type === 'chat_message') {
          setChatMessages(prev => [...prev, {
            role: 'user',
            content: data.user_message,
            timestamp: data.timestamp
          }, {
            role: 'assistant',
            content: data.result?.response || JSON.stringify(data.result),
            agent: data.result?.agent,
            timestamp: data.timestamp
          }]);
        }
      };
      
      wsRef.current.onclose = () => {
        setWsConnected(false);
        setTimeout(connectWebSocket, 3000);
      };
      
      wsRef.current.onerror = () => {
        setWsConnected(false);
      };
    } catch (error) {
      console.error('WebSocket error:', error);
      setTimeout(connectWebSocket, 3000);
    }
  }, []);

  const generateMapNodes = (data) => {
    // Generate nodes based on agent activity
    const baseCoords = { lat: 37.7749, lng: -122.4194 };
    const nodes = [];
    
    const agentNames = ['alert', 'analysis', 'task', 'vision', 'data'];
    agentNames.forEach((agent, i) => {
      const angle = (i / agentNames.length) * Math.PI * 2;
      const radius = 0.02;
      nodes.push({
        id: `agent-${agent}`,
        lat: baseCoords.lat + Math.cos(angle) * radius,
        lng: baseCoords.lng + Math.sin(angle) * radius,
        type: 'agent',
        name: agent,
        active: true,
        connections: agentNames.filter(a => a !== agent).map(a => `agent-${a}`)
      });
    });
    
    // Add data nodes
    const ingestionCount = data.ingestion_stats?.total_ingested || 0;
    for (let i = 0; i < Math.min(ingestionCount, 20); i++) {
      const angle = Math.random() * Math.PI * 2;
      const radius = 0.01 + Math.random() * 0.03;
      nodes.push({
        id: `data-${i}`,
        lat: baseCoords.lat + Math.cos(angle) * radius,
        lng: baseCoords.lng + Math.sin(angle) * radius,
        type: 'data',
        name: `Data ${i + 1}`,
        connections: [`agent-${agentNames[Math.floor(Math.random() * agentNames.length)]}`]
      });
    }
    
    setMapNodes(nodes);
  };

  useEffect(() => {
    connectWebSocket();
    
    // Fetch initial data
    fetchAgents();
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connectWebSocket]);

  const fetchAgents = async () => {
    try {
      const response = await fetch('/api/agents');
      if (response.ok) {
        const data = await response.json();
        setAgents(Object.keys(data));
      }
    } catch (error) {
      console.error('Failed to fetch agents:', error);
    }
  };

  const sendMessage = async (message) => {
    setChatMessages(prev => [...prev, {
      role: 'user',
      content: message,
      timestamp: new Date().toISOString()
    }]);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message })
      });
      
      if (response.ok) {
        const data = await response.json();
        setChatMessages(prev => [...prev, {
          role: 'assistant',
          content: data.response || JSON.stringify(data),
          agent: data.agent,
          timestamp: new Date().toISOString()
        }]);
      }
    } catch (error) {
      setChatMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Connection error. Please try again.',
        timestamp: new Date().toISOString()
      }]);
    }
  };

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Void background */}
      <div className="void-background" />
      
      {/* Animated stars */}
      <div className="stars">
        {stars.map(star => (
          <div
            key={star.id}
            className="star"
            style={{
              left: star.left,
              top: star.top,
              width: `${star.size}px`,
              height: `${star.size}px`,
              animationDelay: star.delay
            }}
          />
        ))}
      </div>
      
      {/* Grid overlay */}
      <div className="grid-overlay opacity-30" />

      {/* Main content */}
      <div className="relative z-10 p-6 lg:p-8">
        {/* Header */}
        <motion.header 
          initial={{ opacity: 0, y: -50 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
              >
                <img src="/ai-icon.svg" alt="AI" className="w-16 h-16" />
              </motion.div>
              <div>
                <h1 className="font-orbitron text-3xl font-bold neon-text neon-text-blue">
                  AI AGENT SYSTEM
                </h1>
                <p className="text-gray-400 text-sm tracking-widest">
                  MULTI-AGENT ORCHESTRATION • 2026
                </p>
              </div>
            </div>
            
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-2">
                <div className={`w-3 h-3 rounded-full ${wsConnected ? 'bg-neon-green pulse-live' : 'bg-red-500'}`} />
                <span className="text-sm text-gray-400">
                  {wsConnected ? 'CONNECTED' : 'DISCONNECTED'}
                </span>
              </div>
              
              <div className="text-right">
                <div className="text-xs text-gray-500">SYSTEM TIME</div>
                <div className="font-orbitron text-neon-blue">
                  {new Date().toLocaleTimeString()}
                </div>
              </div>
            </div>
          </div>
          
          <div className="data-flow-line mt-4" />
        </motion.header>

        {/* Main grid */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          {/* Left column - Chat and Agents */}
          <div className="xl:col-span-1 space-y-6">
            <GlassPanel title="AI ASSISTANT" icon="chat" className="h-[500px]">
              <ChatInterface 
                messages={chatMessages}
                onSendMessage={sendMessage}
                agents={agents}
              />
            </GlassPanel>
            
            <GlassPanel title="AGENT STATUS" icon="agents">
              <AgentStatus agents={agents} stats={stats} />
            </GlassPanel>
          </div>

          {/* Center column - Main dashboard */}
          <div className="xl:col-span-1 space-y-6">
            <GlassPanel 
              title="LIVE STATISTICS" 
              icon="stats"
              flipEnabled
              backContent={<DataFlow stats={stats} />}
            >
              <StatsDisplay stats={stats} />
            </GlassPanel>
            
            <GlassPanel title="REAL-TIME MAP" icon="map" className="h-[400px]">
              <LiveMap nodes={mapNodes} />
            </GlassPanel>
          </div>

          {/* Right column - Data flow and events */}
          <div className="xl:col-span-1 space-y-6">
            <GlassPanel title="DATA INGESTION" icon="data">
              <DataFlow stats={stats} detailed />
            </GlassPanel>
            
            <GlassPanel title="SYSTEM EVENTS" icon="events" className="h-[300px]">
              <EventLog events={events} stats={stats} />
            </GlassPanel>
          </div>
        </div>
      </div>
    </div>
  );
}

// Event log component
function EventLog({ events, stats }) {
  const recentEvents = [
    { type: 'ingestion', message: `${stats.ingestion_stats?.total_ingested || 0} documents ingested`, time: 'now' },
    { type: 'agent', message: 'Analysis agent processed request', time: '2s ago' },
    { type: 'alert', message: `${stats.realtime?.alerts_today || 0} alerts today`, time: '5s ago' },
    { type: 'connection', message: `${stats.realtime?.active_connections || 0} active connections`, time: '10s ago' },
  ];

  return (
    <div className="space-y-2 overflow-y-auto h-full">
      {recentEvents.map((event, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: i * 0.1 }}
          className="flex items-center gap-3 p-2 rounded-lg bg-white/5 border border-white/10"
        >
          <div className={`w-2 h-2 rounded-full ${
            event.type === 'alert' ? 'bg-neon-pink' :
            event.type === 'agent' ? 'bg-neon-purple' :
            event.type === 'ingestion' ? 'bg-neon-green' :
            'bg-neon-blue'
          }`} />
          <span className="text-sm flex-1 text-gray-300">{event.message}</span>
          <span className="text-xs text-gray-500">{event.time}</span>
        </motion.div>
      ))}
    </div>
  );
}

export default App;
