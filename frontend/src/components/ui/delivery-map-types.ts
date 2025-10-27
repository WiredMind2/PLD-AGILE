export interface DeliveryPoint {
  id: string;
  position: [number, number]; // [lat, lng]
  address?: string;
  type: "pickup" | "delivery" | "courier" | "default";
  status?: "pending" | "in-progress" | "completed" | "active";
  deliveryId?: string; // To link pickup and delivery points together
  isHighlighted?: boolean; // NEW: For highlighting functionality
}

export interface RoadSegment {
  start: [number, number]; // [lat, lng]
  end: [number, number]; // [lat, lng]
  street_name?: string;
}

export interface DeliveryMapProps {
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
    delivery: [number, number],
    options?: { pickup_service_s?: number; delivery_service_s?: number }
  ) => Promise<void> | void;
}