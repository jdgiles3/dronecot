import React, { useEffect, useRef, useMemo } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, Circle, useMap } from 'react-leaflet';
import L from 'leaflet';

// Fix for default marker icons in React-Leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

// Custom drone icon
const createDroneIcon = (color = '#ef4444') => {
  return L.divIcon({
    className: 'custom-drone-icon',
    html: `
      <div style="
        width: 24px;
        height: 24px;
        background: ${color};
        border: 2px solid white;
        border-radius: 50%;
        box-shadow: 0 0 10px ${color};
        display: flex;
        align-items: center;
        justify-content: center;
      ">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="white">
          <circle cx="12" cy="12" r="4"/>
          <line x1="12" y1="12" x2="6" y2="6" stroke="white" stroke-width="2"/>
          <line x1="12" y1="12" x2="18" y2="6" stroke="white" stroke-width="2"/>
          <line x1="12" y1="12" x2="6" y2="18" stroke="white" stroke-width="2"/>
          <line x1="12" y1="12" x2="18" y2="18" stroke="white" stroke-width="2"/>
        </svg>
      </div>
    `,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
    popupAnchor: [0, -12]
  });
};

// Map bounds updater component
function MapBoundsUpdater({ markers }) {
  const map = useMap();
  
  useEffect(() => {
    if (markers.length > 0) {
      const bounds = L.latLngBounds(markers.map(m => [m.lat, m.lng]));
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 15 });
    }
  }, [markers, map]);
  
  return null;
}

function MapPanel({ markers, crossTracks }) {
  const defaultCenter = [37.7749, -122.4194]; // San Francisco
  const defaultZoom = 13;

  // Group markers by track ID for drawing paths
  const trackPaths = useMemo(() => {
    const paths = {};
    markers.forEach(marker => {
      if (marker.track_id !== null && marker.track_id !== undefined) {
        if (!paths[marker.track_id]) {
          paths[marker.track_id] = [];
        }
        paths[marker.track_id].push([marker.lat, marker.lng]);
      }
    });
    return paths;
  }, [markers]);

  // Get unique markers (latest position per track)
  const uniqueMarkers = useMemo(() => {
    const latest = {};
    markers.forEach(marker => {
      const key = marker.track_id ?? marker.id;
      if (!latest[key] || new Date(marker.timestamp) > new Date(latest[key].timestamp)) {
        latest[key] = marker;
      }
    });
    return Object.values(latest);
  }, [markers]);

  // Color mapping for different detection classes
  const getMarkerColor = (detectionClass) => {
    const colors = {
      'drone': '#ef4444',
      'aircraft': '#f59e0b',
      'bird': '#22c55e',
      'person': '#3b82f6',
      'vehicle': '#8b5cf6',
      'default': '#6b7280'
    };
    return colors[detectionClass?.toLowerCase()] || colors.default;
  };

  return (
    <div className="h-[400px] rounded-lg overflow-hidden">
      <MapContainer
        center={defaultCenter}
        zoom={defaultZoom}
        className="h-full w-full"
        style={{ background: '#1e293b' }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />
        
        {/* Update bounds when markers change */}
        {uniqueMarkers.length > 0 && <MapBoundsUpdater markers={uniqueMarkers} />}
        
        {/* Draw track paths */}
        {Object.entries(trackPaths).map(([trackId, positions]) => (
          positions.length > 1 && (
            <Polyline
              key={`path-${trackId}`}
              positions={positions}
              pathOptions={{
                color: '#3b82f6',
                weight: 2,
                opacity: 0.6,
                dashArray: '5, 10'
              }}
            />
          )
        ))}
        
        {/* Draw markers */}
        {uniqueMarkers.map((marker) => (
          <React.Fragment key={marker.id}>
            {/* Detection radius circle */}
            <Circle
              center={[marker.lat, marker.lng]}
              radius={50}
              pathOptions={{
                color: getMarkerColor(marker.detection_class),
                fillColor: getMarkerColor(marker.detection_class),
                fillOpacity: 0.2,
                weight: 1
              }}
            />
            
            {/* Marker */}
            <Marker
              position={[marker.lat, marker.lng]}
              icon={createDroneIcon(getMarkerColor(marker.detection_class))}
            >
              <Popup>
                <div className="text-gray-900 min-w-[200px]">
                  <h3 className="font-bold text-lg mb-2">{marker.label}</h3>
                  <div className="space-y-1 text-sm">
                    <p><span className="font-medium">Class:</span> {marker.detection_class}</p>
                    <p><span className="font-medium">Confidence:</span> {(marker.confidence * 100).toFixed(1)}%</p>
                    <p><span className="font-medium">Track ID:</span> {marker.track_id ?? 'N/A'}</p>
                    <p><span className="font-medium">Stream:</span> Camera {(marker.stream_id ?? 0) + 1}</p>
                    <p><span className="font-medium">Lat:</span> {marker.lat.toFixed(6)}</p>
                    <p><span className="font-medium">Lng:</span> {marker.lng.toFixed(6)}</p>
                    <p><span className="font-medium">Time:</span> {new Date(marker.timestamp).toLocaleTimeString()}</p>
                    {marker.metadata?.velocity && (
                      <p>
                        <span className="font-medium">Velocity:</span>{' '}
                        ({marker.metadata.velocity.vx?.toFixed(1)}, {marker.metadata.velocity.vy?.toFixed(1)})
                      </p>
                    )}
                    {marker.metadata?.predicted_next_screen !== null && (
                      <p className="text-green-600 font-medium">
                        Predicted next: Camera {marker.metadata.predicted_next_screen + 1}
                      </p>
                    )}
                  </div>
                </div>
              </Popup>
            </Marker>
          </React.Fragment>
        ))}
      </MapContainer>
      
      {/* Legend */}
      <div className="absolute bottom-4 left-4 glass-dark p-3 rounded-lg z-[1000]">
        <h4 className="text-xs font-medium mb-2">Detection Types</h4>
        <div className="space-y-1">
          {[
            { label: 'Drone', color: '#ef4444' },
            { label: 'Aircraft', color: '#f59e0b' },
            { label: 'Bird', color: '#22c55e' },
            { label: 'Person', color: '#3b82f6' },
            { label: 'Vehicle', color: '#8b5cf6' }
          ].map(item => (
            <div key={item.label} className="flex items-center gap-2 text-xs">
              <div 
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: item.color, boxShadow: `0 0 6px ${item.color}` }}
              />
              <span>{item.label}</span>
            </div>
          ))}
        </div>
      </div>
      
      {/* Stats overlay */}
      <div className="absolute top-4 right-4 glass-dark p-3 rounded-lg z-[1000]">
        <div className="text-xs space-y-1">
          <p><span className="text-gray-400">Active Markers:</span> {uniqueMarkers.length}</p>
          <p><span className="text-gray-400">Track Paths:</span> {Object.keys(trackPaths).length}</p>
          <p><span className="text-gray-400">Cross-Tracks:</span> {crossTracks.length}</p>
        </div>
      </div>
    </div>
  );
}

export default MapPanel;
