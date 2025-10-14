// DeliveryMap.tsx
import { MapContainer, TileLayer, Marker, Popup, Polyline } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

export interface DeliveryPoint {
  id: string;
  position: [number, number]; // [lat, lng]
  address?: string;
  type: 'warehouse' | 'delivery' | 'courier' | 'default';
  status?: 'pending' | 'in-progress' | 'completed' | 'active';
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
  warehouse: createCircularIcon('#3b82f6', '🏢', 'white', 40),
  delivery:  createCircularIcon('#ef4444', '📦', 'white', 40), 
  courier:   createCircularIcon('#22c55e', '🚴', 'white', 40),
  default:   createCircularIcon('#ff7b00ff', '●', 'white', 15),
};

interface DeliveryMapProps {
  points?: DeliveryPoint[];
  center?: [number, number];
  zoom?: number;
  height?: number | string;
  showRouting?: boolean; // Show connecting lines between points
  onPointClick?: (p: DeliveryPoint) => void;
}

export default function DeliveryMap({
  points = [],
  center = [48.8566, 2.3522],
  zoom = 13,
  height = 500,
  showRouting = true,
  onPointClick,
}: DeliveryMapProps) {
  const style = { height: typeof height === 'number' ? `${height}px` : height, width: '100%' };

  // Only show routing lines for non-default points (actual delivery routes)
  const routingPoints = points.filter(p => p.type !== 'default');

  return (
    <MapContainer center={center} zoom={zoom} style={style}>
      <TileLayer
        attribution='&copy; <a href="https://osm.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {/* Markers */}
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
                {p.type === 'warehouse' ? '🏢 Warehouse' :
                 p.type === 'delivery'  ? '📦 Delivery' : 
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

      {/* Simple line connecting points*/}
      {showRouting && routingPoints.length >= 2 && (
        <Polyline 
          positions={routingPoints.map(p => p.position)} 
          color="#16a34a"
          weight={4}
          opacity={0.8}
        />
      )}
    </MapContainer>
  );
}
