// DeliveryMap.tsx
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
} from "react-leaflet";
import { useState } from "react";
import "leaflet/dist/leaflet.css";
import "leaflet.markercluster/dist/MarkerCluster.css";
import "leaflet.markercluster/dist/MarkerCluster.Default.css";
import L from "leaflet";
import {
  DeliveryPoint,
  DeliveryMapProps,
} from "./delivery-map-types";
import {
  getIcon,
  createNumberIcon,
  calculateLabeledPositions,
} from "./delivery-map-utils";
import {
  MapRightClickHandler,
  MapCenterUpdater,
  MapZoomUpdater,
  MapClickHandler,
} from "./delivery-map-components";
import DeliveryMapContextMenu from "./delivery-map-context-menu";

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
if (typeof document !== "undefined") {
  const styleElement = document.createElement("style");
  styleElement.textContent = mapStyles;
  if (!document.head.querySelector("style[data-map-dark-mode]")) {
    styleElement.setAttribute("data-map-dark-mode", "true");
    document.head.appendChild(styleElement);
  }
}

export default function DeliveryMap({
  points = [],
  roadSegments = [],
  center = [45.764043, 4.835659],
  zoom = 13,
  height = 500,
  showRoadNetwork = false, // Show road network by default
  onPointClick,
  routes = [],
  showSegmentLabels = true,
  onCreateRequestFromCoords,
}: DeliveryMapProps) {
  // State for managing highlighted points
  const [highlightedPoints, setHighlightedPoints] = useState<Set<string>>(
    new Set()
  );

  const style = {
    height: typeof height === "number" ? `${height}px` : height,
    width: "100%",
  };

  // Context menu state (screen position + latlng)
  const [ctxMenu, setCtxMenu] = useState<{
    open: boolean;
    x: number;
    y: number;
    latlng?: [number, number];
  }>({ open: false, x: 0, y: 0 });

  // Two-click atomic creation: first set pickup, then set delivery and submit once
  const [pendingPickup, setPendingPickup] = useState<[number, number] | null>(
    null
  );

  // Service durations in seconds (editable in context menu per step)
  const [pickupDurationSec, setPickupDurationSec] = useState<number>(300); // default 5 min
  const [deliveryDurationSec, setDeliveryDurationSec] = useState<number>(300); // default 5 min

  const handleMapContextMenu = (e: L.LeafletMouseEvent) => {
    setCtxMenu({
      open: true,
      x: e.originalEvent.clientX,
      y: e.originalEvent.clientY,
      latlng: [e.latlng.lat, e.latlng.lng],
    });
  };

  // Function to extract delivery ID from point ID
  const getDeliveryId = (pointId: string): string | null => {
    // Extract delivery ID from IDs like "pickup-D1" or "delivery-D1"
    const match = pointId.match(/^(pickup|delivery)-(.+)$/);
    return match ? match[2] : null;
  };

  // Handle point click with highlighting logic
  const handlePointClick = (point: DeliveryPoint) => {
    const deliveryId = getDeliveryId(point.id);

    if (deliveryId) {
      const pickupId = `pickup-${deliveryId}`;
      const deliveryPointId = `delivery-${deliveryId}`;

      // Check if this delivery pair is already highlighted
      const isCurrentlyHighlighted =
        highlightedPoints.has(pickupId) ||
        highlightedPoints.has(deliveryPointId);

      console.log(`🖱️ Clicked on ${point.type} point:`, {
        pointId: point.id,
        deliveryId,
        pickupId,
        deliveryPointId,
        isCurrentlyHighlighted,
        currentHighlights: Array.from(highlightedPoints),
      });

      if (isCurrentlyHighlighted) {
        // Remove highlight from this pair (clear all highlights)
        setHighlightedPoints(new Set());
        console.log(`🌟 Removed all highlights`);
      } else {
        // Clear previous highlights and add highlight to this pair only
        const newSet = new Set<string>();
        newSet.add(pickupId);
        newSet.add(deliveryPointId);
        setHighlightedPoints(newSet);
        console.log(`✨ Set highlights for ${deliveryId} only`);
      }
    }

    // Call the original click handler if provided
    onPointClick?.(point);
  };

  // Build labeled positions for all route segments
  const labeledPositions = calculateLabeledPositions(routes || []);

  return (
    <>
      <MapContainer center={center} zoom={zoom} style={style}>
        <MapClickHandler onMapClick={() => setHighlightedPoints(new Set())} />
        {/* Right-click listener */}
        <MapRightClickHandler onContextMenu={handleMapContextMenu} />
        <MapCenterUpdater target={center ?? [48.8566, 2.3522]} />
        <MapZoomUpdater level={zoom ?? 13} />
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
          className="map-tiles"
        />

        {/* Markers */}
        {points.map((p) => {
          const isHighlighted = highlightedPoints.has(p.id);
          return (
            <Marker
              key={p.id}
              position={p.position}
              icon={getIcon(p.type, isHighlighted)}
              eventHandlers={{
                click: () => handlePointClick(p),
              }}
            >
              <Popup>
                <div>
                  <strong>
                    {p.type === "pickup"
                      ? "📦 Pickup"
                      : p.type === "delivery"
                      ? "🏢 Delivery"
                      : p.type === "courier"
                      ? "🚴 Courier"
                      : p.type === "default"
                      ? "📍 Map Node"
                      : "Unknown"}
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
          );
        })}

        {/* Connecting lines between highlighted pickup-delivery pairs */}
        {Array.from(highlightedPoints).map((pointId) => {
          const deliveryId = getDeliveryId(pointId);
          if (!deliveryId || !pointId.startsWith("pickup-")) return null;

          const pickupPoint = points.find(
            (p) => p.id === `pickup-${deliveryId}`
          );
          const deliveryPoint = points.find(
            (p) => p.id === `delivery-${deliveryId}`
          );

          if (pickupPoint && deliveryPoint) {
            return (
              <Polyline
                key={`connection-${deliveryId}`}
                positions={[pickupPoint.position, deliveryPoint.position]}
                color="#fbbf24"
                weight={4}
                opacity={0.8}
                dashArray="10, 10"
              />
            );
          }
          return null;
        })}

        {/* Road network from XML map */}
        {showRoadNetwork &&
          roadSegments.map((segment, index) => (
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
            color={r.color ?? "#10b981"}
            weight={5}
            opacity={0.85}
          />
        ))}

        {/* Segment number labels (non-interactive) */}
        {showSegmentLabels &&
          labeledPositions.map((lp) => (
            <Marker
              key={`seg-label-${lp.key}`}
              position={lp.pos}
              icon={createNumberIcon(String(lp.index))}
              interactive={false}
            />
          ))}
      </MapContainer>

      {/* Context dropdown menu at cursor position */}
      <DeliveryMapContextMenu
        ctxMenu={ctxMenu}
        setCtxMenu={setCtxMenu}
        pendingPickup={pendingPickup}
        setPendingPickup={setPendingPickup}
        pickupDurationSec={pickupDurationSec}
        setPickupDurationSec={setPickupDurationSec}
        deliveryDurationSec={deliveryDurationSec}
        setDeliveryDurationSec={setDeliveryDurationSec}
        onCreateRequestFromCoords={onCreateRequestFromCoords}
      />
    </>
  );
}
