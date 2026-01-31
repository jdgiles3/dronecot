import React from 'react';
import { motion } from 'framer-motion';

const agentInfo = {
  alert: {
    name: 'Alert Agent',
    icon: '⚠️',
    color: 'neon-pink',
    description: 'Anomaly detection & alerts'
  },
  analysis: {
    name: 'Analysis Agent',
    icon: '📊',
    color: 'neon-purple',
    description: 'Pattern recognition & insights'
  },
  task: {
    name: 'Task Agent',
    icon: '⚡',
    color: 'neon-blue',
    description: 'Automation & code generation'
  },
  vision: {
    name: 'Vision Agent',
    icon: '👁️',
    color: 'neon-green',
    description: 'Image analysis & OCR'
  },
  data: {
    name: 'Data Agent',
    icon: '💾',
    color: 'neon-blue',
    description: 'Database queries & search'
  }
};

function AgentStatus({ agents, stats }) {
  const requestsByAgent = stats.orchestrator_stats?.requests_by_agent || {};

  return (
    <div className="space-y-3">
      {agents.map((agentName, i) => {
        const info = agentInfo[agentName] || {
          name: agentName,
          icon: '🤖',
          color: 'neon-blue',
          description: 'AI Agent'
        };
        
        const requests = requestsByAgent[agentName] || 0;

        return (
          <motion.div
            key={agentName}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.1 }}
            className="flex items-center gap-3 p-3 rounded-lg bg-white/5 border border-white/10 hover:border-white/20 transition-all group"
          >
            {/* Icon */}
            <div className={`w-10 h-10 rounded-lg bg-${info.color}/20 flex items-center justify-center text-xl group-hover:scale-110 transition-transform`}>
              {info.icon}
            </div>

            {/* Info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-medium text-sm">{info.name}</span>
                <div className="w-2 h-2 rounded-full bg-neon-green pulse-live" />
              </div>
              <div className="text-xs text-gray-500 truncate">
                {info.description}
              </div>
            </div>

            {/* Stats */}
            <div className="text-right">
              <div className={`text-lg font-bold text-${info.color} font-orbitron`}>
                {requests}
              </div>
              <div className="text-xs text-gray-500">requests</div>
            </div>
          </motion.div>
        );
      })}

      {agents.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          <div className="text-4xl mb-2">🤖</div>
          <div className="text-sm">Connecting to agents...</div>
        </div>
      )}

      {/* Summary */}
      {agents.length > 0 && (
        <div className="mt-4 pt-4 border-t border-white/10">
          <div className="flex justify-between text-xs text-gray-400">
            <span>{agents.length} agents active</span>
            <span>
              {Object.values(requestsByAgent).reduce((a, b) => a + b, 0)} total requests
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

export default AgentStatus;
