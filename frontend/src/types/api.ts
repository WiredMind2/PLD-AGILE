export interface Intersection {
  id: string;
  latitude: number;
  longitude: number;
}

export interface RoadSegment {
  start: Intersection;
  end: Intersection;
  length_m: number;
  travel_time_s: number;
  street_name: string;
}

export interface Delivery {
  id: string;
  // Backend may return either raw node id strings or Intersection objects
  pickup_addr: string;
  delivery_addr: string;
  pickup_service_s: number;
  delivery_service_s: number;
  warehouse?: string;
  courier?: string;
  hour_departure?: string;
}

export interface Tour {
  courier: string;
  deliveries: [string, string][]; // Array of tuples [pickup_node_id, delivery_node_id]
  total_travel_time_s: number;
  total_service_time_s: number;
  total_distance_m: number;
  route_intersections?: string[]; // Array of intersection IDs for the computed route
  start_time?: string;
  end_time?: string;
}

export interface Map {
  intersections: Intersection[];
  road_segments: RoadSegment[];
  couriers: string[];
  deliveries: Delivery[];
}

// API Error response
export interface ApiError {
  detail: string;
  status_code: number;
}