// DeliveryMap.tsx
import { MapContainer, TileLayer, Marker, Popup, Polyline } from 'react-leaflet';
import MarkerClusterGroup from 'react-leaflet-cluster';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import 'leaflet.markercluster/dist/MarkerCluster.css';
import 'leaflet.markercluster/dist/MarkerCluster.Default.css';

const mapStyles = `
:root {
    --map-tiles-filter: brightness(0.6) invert(1) contrast(3) hue-rotate(200deg) saturate(0.3) brightness(0.7);
}

.dark .map-tiles {
    filter: var(--map-tiles-filter, none);
}

.light .map-tiles {
    filter: none !important;
}
`;

// Inject styles
if (typeof document !== 'undefined') {
  const styleElement = document.createElement('style');
  styleElement.textContent = mapStyles;
  if (!document.head.querySelector('style[data-map-dark-mode]')) {
    styleElement.setAttribute('data-map-dark-mode', 'true');
    document.head.appendChild(styleElement);
  }
}

export interface DeliveryPoint {
  id: string;
  position: [number, number]; // [lat, lng]
  address?: string;
  type: 'pickup' | 'delivery' | 'courier' | 'default';
  status?: 'pending' | 'in-progress' | 'completed' | 'active';
}

export interface RoadSegment {
  start: [number, number]; // [lat, lng]
  end: [number, number]; // [lat, lng]
  street_name?: string;
}

const createCircularIcon = (
  backgroundColor: string, 
  icon: string, 
  textColor: string = 'white',
  size: number = 40
): L.DivIcon => {
  return L.divIcon({
    html: `
      <div style="
        background-color: ${backgroundColor};
        width: ${size}px;
        height: ${size}px;
        border-radius: 50%;
        border: 3px solid white;
        box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: ${Math.floor(size * 0.45)}px;
        color: ${textColor};
        font-weight: bold;
      ">
        ${icon}
      </div>
    `,
    className: 'custom-circular-marker',
    iconSize: [size, size],
    iconAnchor: [size/2, size/2],
    popupAnchor: [0, -size/2]
  });
};

const icons: Record<DeliveryPoint['type'], L.DivIcon> = {
  pickup: createCircularIcon('#ef4444', '📦', 'white', 40),
  delivery:  createCircularIcon('#3b82f6', '🏢', 'white', 40), 
  courier:   createCircularIcon('#22c55e', '🚴', 'white', 40),
  default:   createCircularIcon('#ff7b00ff', '●', 'white', 15),
};

interface DeliveryMapProps {
  points?: DeliveryPoint[];
  roadSegments?: RoadSegment[];
  center?: [number, number];
  zoom?: number;
  height?: number | string;
  showRoadNetwork?: boolean; // Show the road network from XML
  onPointClick?: (p: DeliveryPoint) => void;
}

export default function DeliveryMap({
  points = [],
  roadSegments = [],
  center = [48.8566, 2.3522],
  zoom = 13,
  height = 500,
  showRoadNetwork = false, // Show road network by default
  onPointClick,
}: DeliveryMapProps) {
  const style = { height: typeof height === 'number' ? `${height}px` : height, width: '100%' };

  return (
    <MapContainer center={center} zoom={zoom} style={style}>
      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
        className="map-tiles"
      />

      {/* Markers (clustered when zoomed out) */}
      <MarkerClusterGroup
        chunkedLoading
        showCoverageOnHover={false}
        spiderfyOnMaxZoom
        disableClusteringAtZoom={15}
        maxClusterRadius={25}
      >
        {points.map((p) => (
          <Marker
            key={p.id}
            position={p.position}
            icon={icons[p.type]}
            eventHandlers={{
              click: () => onPointClick?.(p)
            }}
          >
            <Popup>
              <div>
                <strong>
                  {p.type === 'pickup' ? '📦 Pickup' :
                   p.type === 'delivery'  ? '🏢 Delivery' : 
                   p.type === 'courier'   ? '🚴 Courier' :
                   p.type === 'default'   ? '📍 Map Node' : 'Unknown'}
                </strong>
                {p.address && <div style={{ marginTop: 6 }}>{p.address}</div>}
                {p.status && (
                  <div style={{ marginTop: 6, fontSize: 12 }}>
                    Status: {p.status}
                  </div>
                )}
              </div>
            </Popup>
          </Marker>
        ))}
      </MarkerClusterGroup>

      {/* Road network from XML map */}
      {showRoadNetwork && roadSegments.map((segment, index) => (
        <Polyline
          key={`road-${index}`}
          positions={[segment.start, segment.end]}
          color="#6b7280"
          weight={5}
          opacity={1}
        />
      ))}
    </MapContainer>
  );
}