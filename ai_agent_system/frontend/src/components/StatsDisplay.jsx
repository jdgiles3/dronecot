import React from 'react';
import { motion } from 'framer-motion';
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip } from 'recharts';

function StatsDisplay({ stats }) {
  const realtimeStats = stats.realtime || {};
  const orchestratorStats = stats.orchestrator_stats || {};
  const ingestionStats = stats.ingestion_stats || {};

  const statCards = [
    {
      label: 'Messages Processed',
      value: realtimeStats.messages_processed || 0,
      color: 'neon-blue',
      icon: '💬'
    },
    {
      label: 'Active Connections',
      value: realtimeStats.active_connections || 0,
      color: 'neon-green',
      icon: '🔗'
    },
    {
      label: 'Documents Ingested',
      value: ingestionStats.total_ingested || 0,
      color: 'neon-purple',
      icon: '📄'
    },
    {
      label: 'Alerts Today',
      value: realtimeStats.alerts_today || 0,
      color: 'neon-pink',
      icon: '⚠️'
    }
  ];

  // Generate chart data from events per minute
  const chartData = (realtimeStats.events_per_minute || []).slice(-20).map((item, i) => ({
    time: i,
    value: item.count || 0
  }));

  // If no data, generate placeholder
  if (chartData.length === 0) {
    for (let i = 0; i < 20; i++) {
      chartData.push({ time: i, value: Math.floor(Math.random() * 50) + 10 });
    }
  }

  return (
    <div className="space-y-4">
      {/* Stat cards grid */}
      <div className="grid grid-cols-2 gap-3">
        {statCards.map((stat, i) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: i * 0.1 }}
            className="stat-card"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-2xl">{stat.icon}</span>
              <span className={`text-${stat.color} text-xs font-orbitron`}>LIVE</span>
            </div>
            <div className={`text-2xl font-bold text-${stat.color} font-orbitron`}>
              {stat.value.toLocaleString()}
            </div>
            <div className="text-xs text-gray-400 mt-1">
              {stat.label}
            </div>
          </motion.div>
        ))}
      </div>

      {/* Activity chart */}
      <div className="mt-4">
        <div className="text-xs text-gray-400 mb-2 font-orbitron">ACTIVITY TIMELINE</div>
        <div className="h-32 bg-black/20 rounded-lg p-2">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <defs>
                <linearGradient id="lineGradient" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor="#00f0ff" />
                  <stop offset="100%" stopColor="#bf00ff" />
                </linearGradient>
              </defs>
              <XAxis 
                dataKey="time" 
                stroke="rgba(255,255,255,0.1)"
                tick={false}
              />
              <YAxis 
                stroke="rgba(255,255,255,0.1)"
                tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 10 }}
              />
              <Tooltip
                contentStyle={{
                  background: 'rgba(10, 5, 32, 0.95)',
                  border: '1px solid rgba(0, 240, 255, 0.3)',
                  borderRadius: '8px',
                  color: 'white'
                }}
              />
              <Line
                type="monotone"
                dataKey="value"
                stroke="url(#lineGradient)"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, fill: '#00f0ff' }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Additional stats */}
      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="p-2 bg-white/5 rounded-lg">
          <div className="text-lg font-bold text-neon-blue">
            {orchestratorStats.total_requests || 0}
          </div>
          <div className="text-xs text-gray-500">Total Requests</div>
        </div>
        <div className="p-2 bg-white/5 rounded-lg">
          <div className="text-lg font-bold text-neon-green">
            {(orchestratorStats.average_response_time || 0).toFixed(2)}s
          </div>
          <div className="text-xs text-gray-500">Avg Response</div>
        </div>
        <div className="p-2 bg-white/5 rounded-lg">
          <div className="text-lg font-bold text-neon-pink">
            {orchestratorStats.errors || 0}
          </div>
          <div className="text-xs text-gray-500">Errors</div>
        </div>
      </div>
    </div>
  );
}

export default StatsDisplay;
