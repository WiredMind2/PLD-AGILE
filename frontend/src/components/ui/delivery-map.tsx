// DeliveryMap.tsx
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import { useState } from 'react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from './dropdown-menu';
import { Package, Building2, Clipboard, X } from 'lucide-react';
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

// Minimal helper to listen to Leaflet right-clicks
function MapRightClickHandler({ onContextMenu }: { onContextMenu: (e: L.LeafletMouseEvent) => void }) {
  useMapEvents({
    contextmenu: (e) => {
      // Prevent the browser native context menu
      e.originalEvent?.preventDefault?.();
      onContextMenu(e);
    },
  });
  return null;
}

interface DeliveryMapProps {
  points?: DeliveryPoint[];
  roadSegments?: RoadSegment[];
  center?: [number, number];
  zoom?: number;
  height?: number | string;
  showRoadNetwork?: boolean; // Show the road network from XML
  showSegmentLabels?: boolean; // show numbered labels on segments
  onPointClick?: (p: DeliveryPoint) => void;
  routes?: {
    id: string;
    color?: string;
    positions: [number, number][];
  }[];
  onCreateRequestFromCoords?: (
    pickup: [number, number],
    delivery: [number, number]
  ) => Promise<void> | void;
}

export default function DeliveryMap({
  points = [],
  roadSegments = [],
  center = [48.8566, 2.3522],
  zoom = 13,
  height = 500,
  showRoadNetwork = false, // Show road network by default
  onPointClick,
  routes = [],
  showSegmentLabels = true,
  onCreateRequestFromCoords,
}: DeliveryMapProps) {
  const style = { height: typeof height === 'number' ? `${height}px` : height, width: '100%' };

  // Context menu state (screen position + latlng)
  const [ctxMenu, setCtxMenu] = useState<{
    open: boolean;
    x: number;
    y: number;
    latlng?: [number, number];
  }>({ open: false, x: 0, y: 0 });

  // Two-click atomic creation: first set pickup, then set delivery and submit once
  const [pendingPickup, setPendingPickup] = useState<[number, number] | null>(null);

  const handleMapContextMenu = (e: L.LeafletMouseEvent) => {
    setCtxMenu({
      open: true,
      x: e.originalEvent.clientX,
      y: e.originalEvent.clientY,
      latlng: [e.latlng.lat, e.latlng.lng],
    });
  };

  // Helper: midpoint between two lat/lngs
  const midpoint = (a: [number, number], b: [number, number]): [number, number] => [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];

  // create a circular number icon for segments
  const createNumberIcon = (text: string, size = 26): L.DivIcon => {
    return L.divIcon({
      html: `
        <div style="
          background: rgba(16,185,129,0.95);
          color: white;
          width: ${size}px;
          height: ${size}px;
          border-radius: 50%;
          display:flex;
          align-items:center;
          justify-content:center;
          font-size: ${Math.floor(size * 0.5)}px;
          font-weight: 700;
          border: 2px solid white;
          box-shadow: 0 2px 6px rgba(0,0,0,0.3);
        ">` + text + `</div>
      `,
      className: 'segment-number-marker',
      iconSize: [size, size],
      iconAnchor: [size / 2, size / 2],
      popupAnchor: [0, -size / 2],
    });
  };

  // Build labeled positions for all route segments
  const labeledPositions: { pos: [number, number]; index: number; key: string }[] = [];
  if (routes && routes.length > 0) {
    type Seg = { mid: [number, number]; dir: [number, number]; index: number; key: string };
    const allSegments: Seg[] = [];
    for (const r of routes) {
      for (let idx = 0; idx < Math.max(0, r.positions.length - 1); idx++) {
        const start = r.positions[idx];
        const end = r.positions[idx + 1];
        const mid = midpoint(start, end);
  const dx = end[0] - start[0];
  const dy = end[1] - start[1];
        // canonicalize direction so same physical segment has the same canonical direction
        // compare tuples to pick a canonical ordering independent of traversal direction
        const forward = (start[0] < end[0]) || (start[0] === end[0] && start[1] <= end[1]);
        const cdx = forward ? dx : -dx;
        const cdy = forward ? dy : -dy;
        const clen = Math.sqrt(cdx * cdx + cdy * cdy) || 1e-9;
        const canonDir: [number, number] = [cdx / clen, cdy / clen];
        allSegments.push({ mid, dir: canonDir, index: idx + 1, key: `${r.id}-seg-${idx}` });
      }
    }

    // cluster midpoints by proximity (meters)
    const groups: Seg[][] = [];
    const tolMeters = 4; // midpoints closer than this are considered overlapping
    const metersBetween = (a: [number, number], b: [number, number]) => {
      const latAvg = (a[0] + b[0]) / 2;
      const mx = (a[0] - b[0]) * 111320;
      const my = (a[1] - b[1]) * 111320 * Math.cos((latAvg * Math.PI) / 180);
      return Math.sqrt(mx * mx + my * my);
    };

    for (const s of allSegments) {
      let placed = false;
      for (const g of groups) {
        if (metersBetween(g[0].mid, s.mid) <= tolMeters) {
          g.push(s);
          placed = true;
          break;
        }
      }
      if (!placed) groups.push([s]);
    }

    const spacingMeters = 10;
    for (const g of groups) {
      if (g.length === 1) {
        labeledPositions.push({ pos: g[0].mid, index: g[0].index, key: g[0].key });
        continue;
      }
      const m = g.length;
      for (let i = 0; i < m; i++) {
        const s = g[i];
        const offsetMeters = (i - (m - 1) / 2) * spacingMeters;
        const lat = s.mid[0];
        const mperdegLat = 111320;
        const mperdegLng = 111320 * Math.cos((lat * Math.PI) / 180);
        const dLatPerMeter = 1 / mperdegLat;
        const dLngPerMeter = 1 / (mperdegLng || mperdegLat);
        // offset along the perpendicular to the canonical direction so opposite traversals don't cancel
        const normal: [number, number] = [-s.dir[1], s.dir[0]];
        const deltaLat = normal[0] * offsetMeters * dLatPerMeter;
        const deltaLng = normal[1] * offsetMeters * dLngPerMeter;
        labeledPositions.push({ pos: [s.mid[0] + deltaLat, s.mid[1] + deltaLng], index: s.index, key: s.key + `-o${i}` });
      }
    }
  }

  return (
    <>
    <MapContainer center={center} zoom={zoom} style={style}>
      {/* Right-click listener */}
      <MapRightClickHandler onContextMenu={handleMapContextMenu} />
      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
        className="map-tiles"
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

      {/* Computed routes (tours) */}
      {routes.map((r) => (
        <Polyline
          key={`route-${r.id}`}
          positions={r.positions}
          color={r.color ?? '#10b981'}
          weight={5}
          opacity={0.85}
        />
      ))}

      {/* Segment number labels (non-interactive) */}
      {showSegmentLabels && labeledPositions.map((lp) => (
        <Marker key={`seg-label-${lp.key}`} position={lp.pos} icon={createNumberIcon(String(lp.index))} interactive={false} />
      ))}
    </MapContainer>

    {/* Context dropdown menu at cursor position */}
    <DropdownMenu open={ctxMenu.open} onOpenChange={(o) => setCtxMenu((s) => ({ ...s, open: o }))}>
      <DropdownMenuContent
        align="start"
        sideOffset={4}
        // Position absolutely at the cursor using a fixed portal
        style={{ position: 'fixed', left: ctxMenu.x, top: ctxMenu.y, zIndex: 1000 }}
        className="min-w-[14rem] p-2"
        onCloseAutoFocus={(e) => e.preventDefault()}
      >
        <DropdownMenuLabel className="text-xs opacity-70">
          {pendingPickup
            ? `Pickup fixé: ${pendingPickup[0].toFixed(5)}, ${pendingPickup[1].toFixed(5)}`
            : ctxMenu.latlng
              ? `Lat: ${ctxMenu.latlng[0].toFixed(5)}  Lng: ${ctxMenu.latlng[1].toFixed(5)}`
              : 'Position inconnue'}
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        {pendingPickup === null ? (
          <DropdownMenuItem onClick={() => {
            if (ctxMenu.latlng) {
              setPendingPickup(ctxMenu.latlng);
            }
            setCtxMenu((s)=>({ ...s, open: false }));
          }}>
            <Package />
            Commencer une demande: fixer le pickup ici
          </DropdownMenuItem>
        ) : (
          <DropdownMenuItem onClick={async () => {
            if (ctxMenu.latlng && pendingPickup) {
              try {
                await onCreateRequestFromCoords?.(pendingPickup, ctxMenu.latlng);
              } catch (err) {
                console.error('Create request from coords failed', err);
              } finally {
                setPendingPickup(null);
              }
            }
            setCtxMenu((s)=>({ ...s, open: false }));
          }}>
            <Building2 />
            Terminer la demande: fixer la livraison ici
          </DropdownMenuItem>
        )}
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={async () => {
          if (ctxMenu.latlng) {
            try {
              await navigator.clipboard.writeText(`${ctxMenu.latlng[0]}, ${ctxMenu.latlng[1]}`);
            } catch (err) {
              console.error('Clipboard error', err);
            }
          }
          setCtxMenu((s)=>({ ...s, open: false }));
        }}>
          <Clipboard />
          Copier les coordonnées
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        {pendingPickup !== null && (
          <DropdownMenuItem onClick={() => { setPendingPickup(null); setCtxMenu((s)=>({ ...s, open: false })); }}>
            <X />
            Annuler la demande en cours
          </DropdownMenuItem>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
    </>
  );
}