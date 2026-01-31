import React from 'react';
import { motion } from 'framer-motion';
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from 'recharts';

function DataFlow({ stats, detailed = false }) {
  const ingestionStats = stats.ingestion_stats || {};
  const byType = ingestionStats.by_type || {};

  // Prepare pie chart data
  const pieData = Object.entries(byType).map(([type, count]) => ({
    name: type || 'unknown',
    value: count
  }));

  // If no data, show placeholder
  if (pieData.length === 0) {
    pieData.push(
      { name: '.pdf', value: 45 },
      { name: '.txt', value: 30 },
      { name: '.json', value: 15 },
      { name: '.csv', value: 10 }
    );
  }

  const COLORS = ['#00f0ff', '#bf00ff', '#ff00aa', '#00ff88', '#ffaa00'];

  // Bar chart data for detailed view
  const barData = [
    { name: 'Mon', ingested: 120, processed: 115 },
    { name: 'Tue', ingested: 150, processed: 145 },
    { name: 'Wed', ingested: 180, processed: 175 },
    { name: 'Thu', ingested: 140, processed: 138 },
    { name: 'Fri', ingested: 200, processed: 195 },
    { name: 'Sat', ingested: 80, processed: 78 },
    { name: 'Sun', ingested: 60, processed: 58 }
  ];

  return (
    <div className="space-y-4">
      {/* Summary stats */}
      <div className="grid grid-cols-2 gap-3">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="stat-card text-center"
        >
          <div className="text-3xl font-bold text-neon-blue font-orbitron">
            {(ingestionStats.total_ingested || 0).toLocaleString()}
          </div>
          <div className="text-xs text-gray-400 mt-1">Total Ingested</div>
        </motion.div>
        
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.1 }}
          className="stat-card text-center"
        >
          <div className="text-3xl font-bold text-neon-purple font-orbitron">
            {formatBytes(ingestionStats.total_bytes || 0)}
          </div>
          <div className="text-xs text-gray-400 mt-1">Total Size</div>
        </motion.div>
      </div>

      {/* Pie chart - File types */}
      <div>
        <div className="text-xs text-gray-400 mb-2 font-orbitron">FILE TYPES</div>
        <div className="h-40 flex items-center">
          <div className="w-1/2 h-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={30}
                  outerRadius={50}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    background: 'rgba(10, 5, 32, 0.95)',
                    border: '1px solid rgba(0, 240, 255, 0.3)',
                    borderRadius: '8px',
                    color: 'white'
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="w-1/2 space-y-1">
            {pieData.slice(0, 5).map((item, i) => (
              <div key={item.name} className="flex items-center gap-2 text-xs">
                <div 
                  className="w-3 h-3 rounded"
                  style={{ backgroundColor: COLORS[i % COLORS.length] }}
                />
                <span className="text-gray-400 flex-1">{item.name}</span>
                <span className="font-mono">{item.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Detailed view - Bar chart */}
      {detailed && (
        <div>
          <div className="text-xs text-gray-400 mb-2 font-orbitron">WEEKLY ACTIVITY</div>
          <div className="h-32">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={barData}>
                <XAxis 
                  dataKey="name" 
                  stroke="rgba(255,255,255,0.2)"
                  tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 10 }}
                />
                <YAxis 
                  stroke="rgba(255,255,255,0.2)"
                  tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 10 }}
                />
                <Tooltip
                  contentStyle={{
                    background: 'rgba(10, 5, 32, 0.95)',
                    border: '1px solid rgba(0, 240, 255, 0.3)',
                    borderRadius: '8px',
                    color: 'white'
                  }}
                />
                <Bar dataKey="ingested" fill="#00f0ff" radius={[4, 4, 0, 0]} />
                <Bar dataKey="processed" fill="#bf00ff" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Data flow animation */}
      <div className="relative h-8 overflow-hidden rounded-lg bg-black/30">
        <div className="absolute inset-0 flex items-center">
          {[...Array(5)].map((_, i) => (
            <motion.div
              key={i}
              className="absolute w-20 h-1 rounded-full"
              style={{
                background: `linear-gradient(90deg, transparent, ${COLORS[i % COLORS.length]}, transparent)`
              }}
              animate={{
                x: ['-100%', '500%']
              }}
              transition={{
                duration: 3,
                delay: i * 0.5,
                repeat: Infinity,
                ease: 'linear'
              }}
            />
          ))}
        </div>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-xs text-gray-400 font-orbitron">DATA FLOW ACTIVE</span>
        </div>
      </div>

      {/* Error rate */}
      <div className="flex items-center justify-between text-xs">
        <span className="text-gray-400">Error Rate</span>
        <div className="flex items-center gap-2">
          <div className="w-24 h-2 bg-black/30 rounded-full overflow-hidden">
            <div 
              className="h-full bg-neon-green rounded-full"
              style={{ width: `${100 - (ingestionStats.errors || 0)}%` }}
            />
          </div>
          <span className="text-neon-green font-mono">
            {(100 - (ingestionStats.errors || 0)).toFixed(1)}%
          </span>
        </div>
      </div>
    </div>
  );
}

function formatBytes(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

export default DataFlow;
