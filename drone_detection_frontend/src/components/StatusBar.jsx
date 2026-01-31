import React from 'react';

function StatusBar({ wsConnected, mistralConnected, systemStatus }) {
  return (
    <div className="flex items-center gap-4 text-sm">
      {/* WebSocket Status */}
      <div className="flex items-center gap-2">
        <span className={`status-dot ${wsConnected ? 'online' : 'offline'}`}></span>
        <span className="text-gray-400">
          {wsConnected ? 'Live' : 'Disconnected'}
        </span>
      </div>

      {/* Mistral Status */}
      <div className="flex items-center gap-2">
        <span className={`status-dot ${mistralConnected ? 'online' : 'warning'}`}></span>
        <span className="text-gray-400">
          AI {mistralConnected ? 'Ready' : 'Offline'}
        </span>
      </div>

      {/* System Stats */}
      {systemStatus && (
        <>
          <div className="h-4 w-px bg-white/20"></div>
          <div className="flex items-center gap-4 text-gray-400">
            <span>
              <span className="text-white font-medium">{systemStatus.active_streams}</span> streams
            </span>
            <span>
              <span className="text-white font-medium">{systemStatus.total_detections}</span> detections
            </span>
            <span>
              <span className="text-white font-medium">{systemStatus.active_tracks}</span> tracks
            </span>
          </div>
        </>
      )}
    </div>
  );
}

export default StatusBar;
