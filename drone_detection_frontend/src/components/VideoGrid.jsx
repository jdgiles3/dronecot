import React, { useMemo } from 'react';

function VideoGrid({ frames, detections, crossTracks, selectedStream, onStreamSelect }) {
  // Group detections by stream
  const detectionsByStream = useMemo(() => {
    const grouped = {};
    detections.forEach(det => {
      if (!grouped[det.stream_id]) {
        grouped[det.stream_id] = [];
      }
      grouped[det.stream_id].push(det);
    });
    return grouped;
  }, [detections]);

  // Get cross-track predictions for visualization
  const trackPredictions = useMemo(() => {
    const predictions = {};
    crossTracks.forEach(track => {
      if (track.predicted_screens && track.predicted_screens.length > 0) {
        track.predicted_screens.forEach(screenId => {
          if (!predictions[screenId]) {
            predictions[screenId] = [];
          }
          predictions[screenId].push({
            trackId: track.track_id,
            fromScreen: track.current_screen,
            velocity: track.velocity
          });
        });
      }
    });
    return predictions;
  }, [crossTracks]);

  const streams = [0, 1, 2, 3, 4, 5];

  return (
    <div className="glass p-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
          Video Feeds (6 Cameras)
        </h2>
        <div className="text-sm text-gray-400">
          {Object.keys(frames).length} active streams | {detections.length} detections
        </div>
      </div>

      {/* 2x3 Grid with gaps */}
      <div className="grid grid-cols-3 gap-3">
        {streams.map((streamId) => (
          <VideoPlayer
            key={streamId}
            streamId={streamId}
            frame={frames[streamId]}
            detections={detectionsByStream[streamId] || []}
            predictions={trackPredictions[streamId] || []}
            isSelected={selectedStream === streamId}
            onClick={() => onStreamSelect(streamId)}
          />
        ))}
      </div>

      {/* Cross-screen tracking visualization */}
      {crossTracks.length > 0 && (
        <div className="mt-4 p-3 glass-dark rounded-lg">
          <h3 className="text-sm font-medium mb-2 text-blue-400">Active Cross-Screen Tracks</h3>
          <div className="flex flex-wrap gap-2">
            {crossTracks.map(track => (
              <div 
                key={track.track_id}
                className="px-3 py-1 bg-blue-500/20 rounded-full text-xs flex items-center gap-2"
              >
                <span className="font-mono">ID: {track.track_id}</span>
                <span className="text-gray-400">Screen {track.current_screen}</span>
                {track.predicted_screens.length > 0 && (
                  <span className="text-green-400">
                    → {track.predicted_screens.join(', ')}
                  </span>
                )}
                <span className="text-yellow-400">
                  ({track.screens_crossed} crossed)
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function VideoPlayer({ streamId, frame, detections, predictions, isSelected, onClick }) {
  const hasDetections = detections.length > 0;
  const hasPredictions = predictions.length > 0;

  return (
    <div 
      className={`video-container aspect-video cursor-pointer ${isSelected ? 'active' : ''} ${hasDetections ? 'ring-2 ring-red-500/50' : ''}`}
      onClick={onClick}
    >
      {/* Video frame */}
      {frame ? (
        <img 
          src={`data:image/jpeg;base64,${frame}`}
          alt={`Stream ${streamId}`}
          className="w-full h-full object-cover"
        />
      ) : (
        <div className="w-full h-full flex items-center justify-center bg-gray-800">
          <div className="text-center">
            <svg className="w-12 h-12 mx-auto text-gray-600 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
            <p className="text-gray-500 text-sm">Connecting...</p>
          </div>
        </div>
      )}

      {/* Stream label */}
      <div className="absolute top-2 left-2 px-2 py-1 bg-black/60 rounded text-xs font-mono">
        CAM {streamId + 1}
      </div>

      {/* Detection count badge */}
      {hasDetections && (
        <div className="absolute top-2 right-2 px-2 py-1 bg-red-500/80 rounded text-xs font-bold">
          {detections.length} detected
        </div>
      )}

      {/* Prediction indicator */}
      {hasPredictions && (
        <div className="absolute bottom-2 left-2 px-2 py-1 bg-green-500/80 rounded text-xs">
          Incoming: {predictions.map(p => `ID ${p.trackId}`).join(', ')}
        </div>
      )}

      {/* Detection info overlay */}
      {hasDetections && (
        <div className="absolute bottom-2 right-2 max-w-[60%]">
          {detections.slice(0, 2).map((det, idx) => (
            <div 
              key={idx}
              className="px-2 py-1 bg-black/70 rounded text-xs mb-1 truncate"
            >
              {det.bounding_box.class_name} ({(det.bounding_box.confidence * 100).toFixed(0)}%)
              {det.predicted_next_screen !== null && (
                <span className="text-green-400 ml-1">→ {det.predicted_next_screen}</span>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Selection indicator */}
      {isSelected && (
        <div className="absolute inset-0 border-4 border-blue-500 rounded-lg pointer-events-none">
          <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
            <div className="w-16 h-16 border-2 border-blue-400 rounded-full animate-ping opacity-50"></div>
          </div>
        </div>
      )}
    </div>
  );
}

export default VideoGrid;
