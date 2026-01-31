import React, { useMemo } from 'react';

function MetadataPanel({ detections, crossTracks, selectedStream }) {
  // Filter detections for selected stream or show all
  const filteredDetections = useMemo(() => {
    if (selectedStream !== null) {
      return detections.filter(d => d.stream_id === selectedStream);
    }
    return detections;
  }, [detections, selectedStream]);

  // Get latest detection per track
  const latestByTrack = useMemo(() => {
    const latest = {};
    filteredDetections.forEach(det => {
      const trackId = det.bounding_box?.track_id;
      if (trackId !== null && trackId !== undefined) {
        if (!latest[trackId] || new Date(det.timestamp) > new Date(latest[trackId].timestamp)) {
          latest[trackId] = det;
        }
      }
    });
    return Object.values(latest);
  }, [filteredDetections]);

  // Calculate statistics
  const stats = useMemo(() => {
    const classCounts = {};
    filteredDetections.forEach(det => {
      const cls = det.bounding_box?.class_name || 'unknown';
      classCounts[cls] = (classCounts[cls] || 0) + 1;
    });

    const avgConfidence = filteredDetections.length > 0
      ? filteredDetections.reduce((sum, d) => sum + (d.bounding_box?.confidence || 0), 0) / filteredDetections.length
      : 0;

    return {
      total: filteredDetections.length,
      uniqueTracks: latestByTrack.length,
      classCounts,
      avgConfidence
    };
  }, [filteredDetections, latestByTrack]);

  return (
    <div className="metadata-panel space-y-4 max-h-[400px] overflow-y-auto">
      {/* Filter indicator */}
      {selectedStream !== null && (
        <div className="px-3 py-2 bg-blue-500/20 rounded-lg text-sm">
          Showing Camera {selectedStream + 1} only
        </div>
      )}

      {/* Statistics */}
      <div className="glass-dark p-3 rounded-lg">
        <h4 className="text-sm font-medium mb-2 text-blue-400">Statistics</h4>
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="metadata-item">
            <span className="text-gray-400">Total Detections</span>
            <span className="font-mono">{stats.total}</span>
          </div>
          <div className="metadata-item">
            <span className="text-gray-400">Unique Tracks</span>
            <span className="font-mono">{stats.uniqueTracks}</span>
          </div>
          <div className="metadata-item">
            <span className="text-gray-400">Avg Confidence</span>
            <span className="font-mono">{(stats.avgConfidence * 100).toFixed(1)}%</span>
          </div>
          <div className="metadata-item">
            <span className="text-gray-400">Cross-Tracks</span>
            <span className="font-mono">{crossTracks.length}</span>
          </div>
        </div>
      </div>

      {/* Class breakdown */}
      {Object.keys(stats.classCounts).length > 0 && (
        <div className="glass-dark p-3 rounded-lg">
          <h4 className="text-sm font-medium mb-2 text-blue-400">Detection Classes</h4>
          <div className="space-y-1">
            {Object.entries(stats.classCounts).map(([cls, count]) => (
              <div key={cls} className="flex items-center justify-between text-xs">
                <span className="capitalize">{cls}</span>
                <div className="flex items-center gap-2">
                  <div 
                    className="h-2 bg-blue-500 rounded"
                    style={{ width: `${Math.min(count * 10, 100)}px` }}
                  />
                  <span className="font-mono w-8 text-right">{count}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Live detections feed */}
      <div className="glass-dark p-3 rounded-lg">
        <h4 className="text-sm font-medium mb-2 text-blue-400">Live Feed</h4>
        <div className="space-y-2 max-h-[200px] overflow-y-auto">
          {latestByTrack.length === 0 ? (
            <p className="text-xs text-gray-500">No active detections</p>
          ) : (
            latestByTrack.slice(0, 10).map((det, idx) => (
              <div 
                key={idx}
                className="p-2 bg-white/5 rounded text-xs fade-in"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-medium capitalize">
                    {det.bounding_box?.class_name}
                  </span>
                  <span className="text-gray-400">
                    ID: {det.bounding_box?.track_id}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-1 text-gray-400">
                  <span>Cam {det.stream_id + 1}</span>
                  <span>{(det.bounding_box?.confidence * 100).toFixed(0)}%</span>
                  {det.latitude && (
                    <span className="col-span-2 font-mono text-[10px]">
                      {det.latitude.toFixed(4)}, {det.longitude.toFixed(4)}
                    </span>
                  )}
                  {det.predicted_next_screen !== null && (
                    <span className="col-span-2 text-green-400">
                      → Cam {det.predicted_next_screen + 1}
                    </span>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Cross-screen tracks detail */}
      {crossTracks.length > 0 && (
        <div className="glass-dark p-3 rounded-lg">
          <h4 className="text-sm font-medium mb-2 text-blue-400">Cross-Screen Tracks</h4>
          <div className="space-y-2">
            {crossTracks.map(track => (
              <div 
                key={track.track_id}
                className="p-2 bg-white/5 rounded text-xs"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-medium">Track {track.track_id}</span>
                  <span className="text-yellow-400">
                    {track.screens_crossed} screens
                  </span>
                </div>
                <div className="text-gray-400">
                  <p>Current: Camera {track.current_screen + 1}</p>
                  {track.predicted_screens.length > 0 && (
                    <p className="text-green-400">
                      Next: Camera {track.predicted_screens.map(s => s + 1).join(', ')}
                    </p>
                  )}
                  {track.velocity && (
                    <p className="font-mono text-[10px]">
                      Velocity: ({track.velocity.vx?.toFixed(1)}, {track.velocity.vy?.toFixed(1)})
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* JSON export */}
      <div className="text-center">
        <button
          onClick={() => {
            const data = {
              detections: filteredDetections,
              crossTracks,
              stats,
              timestamp: new Date().toISOString()
            };
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `detections_${Date.now()}.json`;
            a.click();
          }}
          className="text-xs text-blue-400 hover:underline"
        >
          Export JSON
        </button>
      </div>
    </div>
  );
}

export default MetadataPanel;
