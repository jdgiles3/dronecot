import React, { useEffect, useRef, useMemo } from 'react';
import { MapContainer, TileLayer, CircleMarker, Polyline, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet.markercluster';

// Fix Leaflet icons
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

// Cluster layer component
function ClusterLayer({ nodes }) {
  const map = useMap();
  const clusterRef = useRef(null);

  useEffect(() => {
    if (!map) return;

    // Create marker cluster group
    const cluster = L.markerClusterGroup({
      iconCreateFunction: (cluster) => {
        const count = cluster.getChildCount();
        return L.divIcon({
          html: `<div class="flex items-center justify-center w-10 h-10 rounded-full bg-neon-blue/30 border-2 border-neon-blue text-white font-bold">${count}</div>`,
          className: 'custom-cluster-icon',
          iconSize: [40, 40]
        });
      },
      maxClusterRadius: 50,
      spiderfyOnMaxZoom: true
    });

    // Add markers
    nodes.filter(n => n.type === 'data').forEach(node => {
      const marker = L.circleMarker([node.lat, node.lng], {
        radius: 6,
        fillColor: '#00ff88',
        color: '#00ff88',
        weight: 1,
        opacity: 0.8,
        fillOpacity: 0.5
      });
      
      marker.bindPopup(`
        <div class="text-sm">
          <div class="font-bold text-neon-green">${node.name}</div>
          <div class="text-gray-400">Type: ${node.type}</div>
        </div>
      `);
      
      cluster.addLayer(marker);
    });

    map.addLayer(cluster);
    clusterRef.current = cluster;

    return () => {
      map.removeLayer(cluster);
    };
  }, [map, nodes]);

  return null;
}

function LiveMap({ nodes }) {
  const defaultCenter = [37.7749, -122.4194];
  const defaultZoom = 13;

  // Get agent nodes
  const agentNodes = useMemo(() => 
    nodes.filter(n => n.type === 'agent'),
    [nodes]
  );

  // Generate connection lines
  const connections = useMemo(() => {
    const lines = [];
    nodes.forEach(node => {
      if (node.connections) {
        node.connections.forEach(targetId => {
          const target = nodes.find(n => n.id === targetId);
          if (target) {
            lines.push({
              id: `${node.id}-${targetId}`,
              positions: [[node.lat, node.lng], [target.lat, target.lng]]
            });
          }
        });
      }
    });
    return lines;
  }, [nodes]);

  const getNodeColor = (type) => {
    switch (type) {
      case 'agent': return '#00f0ff';
      case 'data': return '#00ff88';
      case 'alert': return '#ff00aa';
      default: return '#bf00ff';
    }
  };

  return (
    <div className="h-full w-full rounded-lg overflow-hidden relative">
      <MapContainer
        center={defaultCenter}
        zoom={defaultZoom}
        className="h-full w-full"
        style={{ background: '#0a0520' }}
      >
        <TileLayer
          attribution='&copy; <a href="https://carto.com/">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />

        {/* Connection lines */}
        {connections.map(conn => (
          <Polyline
            key={conn.id}
            positions={conn.positions}
            pathOptions={{
              color: '#00f0ff',
              weight: 1,
              opacity: 0.3,
              dashArray: '5, 10'
            }}
          />
        ))}

        {/* Agent nodes */}
        {agentNodes.map(node => (
          <CircleMarker
            key={node.id}
            center={[node.lat, node.lng]}
            radius={12}
            pathOptions={{
              fillColor: getNodeColor(node.type),
              color: getNodeColor(node.type),
              weight: 2,
              opacity: 1,
              fillOpacity: 0.6
            }}
          >
            <Popup>
              <div className="text-sm min-w-[150px]">
                <div className="font-bold text-neon-blue mb-1">{node.name.toUpperCase()} AGENT</div>
                <div className="text-gray-400">Status: {node.active ? 'Active' : 'Inactive'}</div>
                <div className="text-gray-400">Connections: {node.connections?.length || 0}</div>
                <div className="text-xs text-gray-500 mt-1">
                  {node.lat.toFixed(4)}, {node.lng.toFixed(4)}
                </div>
              </div>
            </Popup>
          </CircleMarker>
        ))}

        {/* Cluster layer for data nodes */}
        <ClusterLayer nodes={nodes} />
      </MapContainer>

      {/* Legend */}
      <div className="absolute bottom-4 left-4 glass-panel p-3 z-[1000]">
        <div className="text-xs font-orbitron mb-2 text-gray-400">LEGEND</div>
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-neon-blue" />
            <span className="text-xs">Agent Node</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-neon-green" />
            <span className="text-xs">Data Node</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-0.5 bg-neon-blue opacity-50" style={{ borderStyle: 'dashed' }} />
            <span className="text-xs">Connection</span>
          </div>
        </div>
      </div>

      {/* Stats overlay */}
      <div className="absolute top-4 right-4 glass-panel p-3 z-[1000]">
        <div className="text-xs space-y-1">
          <div className="flex justify-between gap-4">
            <span className="text-gray-400">Nodes:</span>
            <span className="text-neon-blue font-mono">{nodes.length}</span>
          </div>
          <div className="flex justify-between gap-4">
            <span className="text-gray-400">Connections:</span>
            <span className="text-neon-purple font-mono">{connections.length}</span>
          </div>
          <div className="flex justify-between gap-4">
            <span className="text-gray-400">Agents:</span>
            <span className="text-neon-green font-mono">{agentNodes.length}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default LiveMap;
